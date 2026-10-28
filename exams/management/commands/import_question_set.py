
from datetime import date
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction
from django.utils import timezone

from exams.models import DailyExam, ExamQuestion, ExamOption


class Command(BaseCommand):
    help = (
        "Copy one source MCQ question set into the separate exam database "
        "for a specific date."
    )

    def add_arguments(self, parser):
        parser.add_argument("source_set_id", type=str)
        parser.add_argument(
            "--date",
            type=date.fromisoformat,
            default=timezone.localdate,
            help="Exam date in YYYY-MM-DD format; defaults to today.",
        )
        parser.add_argument(
            "--created-by",
            type=int,
            default=None,
            help="Optional local ExamUser ID for the exam creator.",
        )
        parser.add_argument(
            "--duration",
            type=int,
            default=50,
            help="Exam duration in minutes (1–300). Defaults to 50.",
        )

    def handle(self, *args, **options):
        try:
            source_set_id = str(UUID(options["source_set_id"]))
        except (ValueError, TypeError, AttributeError) as exc:
            raise CommandError("Invalid source question-set UUID.") from exc

        exam_date = options["date"] or timezone.localdate()
        created_by_id = options["created_by"]
        duration = options["duration"]

        if not 1 <= duration <= 300:
            raise CommandError("Duration must be between 1 and 300 minutes.")

        # Read the source set and its questions/options without modifying it.
        source = connections["source_mcq"]

        try:
            with source.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, title, description, category, is_active
                    FROM mcq_questionset
                    WHERE id = %s
                    """,
                    [source_set_id],
                )
                source_set = cursor.fetchone()

                if source_set is None:
                    raise CommandError("The source question set was not found.")

                set_id, title, description, category, is_active = source_set

                if not is_active:
                    raise CommandError(
                        "This question set is inactive. Activate it in the "
                        "source system before importing."
                    )

                cursor.execute(
                    """
                    SELECT
                        q.id,
                        q.question_type,
                        q.text,
                        q.image,
                        q.audio,
                        q.explanation,
                        q.points,
                        q.order,
                        COALESCE(s.name, '')
                    FROM mcq_question q
                    LEFT JOIN mcq_mcqsection s ON s.id = q.section_id
                    WHERE q.question_set_id = %s
                    ORDER BY q.order, q.id
                    """,
                    [source_set_id],
                )
                questions = cursor.fetchall()

                if not questions:
                    raise CommandError("This set contains no questions.")

                question_ids = [row[0] for row in questions]
                placeholders = ", ".join(["%s"] * len(question_ids))

                cursor.execute(
                    f"""
                    SELECT
                        id, question_id, text, image, audio, is_correct, "order"
                    FROM mcq_option
                    WHERE question_id IN ({placeholders})
                    ORDER BY question_id, "order", id
                    """,
                    question_ids,
                )
                option_rows = cursor.fetchall()
        finally:
            source.close()

        options_by_question = {}
        for row in option_rows:
            option_id, question_id, text, image, audio, is_correct, order = row
            options_by_question.setdefault(question_id, []).append(
                {
                    "text": text or "",
                    "image": image or "",
                    "audio": audio or "",
                    "is_correct": bool(is_correct),
                    "order": order or 0,
                }
            )

        # Fail before creating anything if a question has no options.
        questions_without_options = [
            row[0]
            for row in questions
            if not options_by_question.get(row[0])
        ]
        if questions_without_options:
            raise CommandError(
                f"{len(questions_without_options)} question(s) have no options. "
                "Nothing was imported."
            )

        # All writes happen only on the new project's default database.
        with transaction.atomic(using="default"):
            exam = (
                DailyExam.objects.using("default")
                .filter(
                    source_set_id=source_set_id,
                    exam_date=exam_date,
                )
                .first()
            )

            # Repair the known legacy Set 1 record if its UUID was not saved.
            if (
                exam is None
                and source_set_id == "cc3e88d1-f185-4360-8349-5ffdddcf3944"
            ):
                legacy_exam = (
                    DailyExam.objects.using("default")
                    .filter(pk=2, exam_date=exam_date, title="Set 1")
                    .first()
                )

                if legacy_exam and not ExamQuestion.objects.using("default").filter(
                    daily_exam=legacy_exam
                ).exists():
                    exam = legacy_exam

            if exam:
                existing_questions = ExamQuestion.objects.using("default").filter(
                    daily_exam=exam
                ).count()

                if existing_questions:
                    raise CommandError(
                        f"Exam '{exam.title}' already has {existing_questions} "
                        "questions. Nothing was changed."
                    )

                # Repair an existing empty exam instead of creating a duplicate.
                exam.title = title
                exam.duration_minutes = duration
                exam.total_questions = len(questions)
                exam.is_published = False
                exam.source_set_id = source_set_id
                exam.source_category = category or ""
                exam.source_description = description or ""
                exam.save(using="default")
            else:
                exam = DailyExam.objects.using("default").create(
                    title=title,
                    exam_date=exam_date,
                    duration_minutes=duration,
                    total_questions=len(questions),
                    is_published=False,
                    source_set_id=source_set_id,
                    source_category=category or "",
                    source_description=description or "",
                    created_by=None,
                )

            created_by = None
            if created_by_id is not None:
                from django.contrib.auth import get_user_model

                User = get_user_model()
                try:
                    created_by = User.objects.using("default").get(
                        pk=created_by_id
                    )
                except User.DoesNotExist as exc:
                    raise CommandError(
                        f"Local user ID {created_by_id} does not exist."
                    ) from exc


            for question_id, qtype, text, image, audio, explanation, points, order, section_name in questions:
                exam_question = ExamQuestion.objects.using("default").create(
                    daily_exam=exam,
                    source_question_id=str(question_id),
                    question_type=qtype or "text",
                    question_text=text or "",
                    image_url=image or "",
                    audio_url=audio or "",
                    explanation=explanation or "",
                    points=max(0, points or 0),
                    section_name=section_name or "",
                    order=order or 0,
                )

                ExamOption.objects.using("default").bulk_create(
                    [
                        ExamOption(
                            question=exam_question,
                            option_text=option["text"],
                            image_url=option["image"],
                            audio_url=option["audio"],
                            is_correct=option["is_correct"],
                            order=option["order"],
                        )
                        for option in options_by_question[question_id]
                    ]
                )

        self.stdout.write(self.style.SUCCESS(
            f"Imported '{title}' for {exam_date}.\n"
            f"Questions: {len(questions)}\n"
            f"Duration: {duration} minutes\n"
            f"Published: No (review before publishing)\n"
            f"Local exam ID: {exam.pk}"
        ))

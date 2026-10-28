
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import ExamAttempt


@transaction.atomic
def finalize_attempt(attempt_id):
    attempt = (
        ExamAttempt.objects
        .select_for_update()
        .select_related("daily_exam")
        .get(pk=attempt_id)
    )

    if attempt.is_submitted:
        return attempt

    now = timezone.now()

    # Never allow a submission to extend the server-controlled deadline.
    submitted_time = min(now, attempt.deadline_at)

    total_questions = attempt.daily_exam.questions.count()

    correct_answers = sum(
        1
        for answer in attempt.answers.select_related(
            "selected_option"
        ).all()
        if answer.selected_option_id
        and answer.selected_option.is_correct
        and answer.selected_option.question_id == answer.question_id
    )

    percentage = (
        (correct_answers / total_questions) * 100
        if total_questions
        else 0
    )

    elapsed_seconds = max(
        0,
        int((submitted_time - attempt.started_at).total_seconds()),
    )

    attempt.correct_answers = correct_answers
    attempt.score = correct_answers
    attempt.percentage = round(percentage, 2)
    attempt.duration_seconds = elapsed_seconds
    attempt.submitted_at = submitted_time
    attempt.is_submitted = True

    attempt.save(
        update_fields=[
            "correct_answers",
            "score",
            "percentage",
            "duration_seconds",
            "submitted_at",
            "is_submitted",
        ]
    )

    return attempt


import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from results.models import ExamAttempt, StudentAnswer
from results.services import finalize_attempt
from .models import DailyExam


CLOUDINARY_CLOUD_NAME = "zxqttnxc"


def cloudinary_asset_url(value, resource_type="image"):
    """Convert a stored Cloudinary public ID into a delivery URL."""
    from urllib.parse import quote

    if not value:
        return ""

    value = value.strip().replace("\\", "/")

    if value.startswith(("https://", "http://")):
        return value

    public_id = value.lstrip("/")
    return (
        f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/"
        f"{resource_type}/upload/{quote(public_id, safe='/')}"
    )


@login_required
def exam_home(request):
    if request.user.is_staff:
        return redirect("admin:index")

    today = timezone.localdate()

    daily_exam = DailyExam.objects.filter(
        exam_date=today,
        is_published=True,
    ).first()

    attempt = None
    if daily_exam:
        attempt = ExamAttempt.objects.filter(
            daily_exam=daily_exam,
            student=request.user,
        ).first()

    return render(
        request,
        "exams/home.html",
        {
            "daily_exam": daily_exam,
            "attempt": attempt,
            "today": today,
        },
    )


@login_required
@require_POST
def start_exam(request, exam_id):
    if request.user.is_staff:
        return redirect("admin:index")

    now = timezone.now()
    today = timezone.localdate()

    daily_exam = get_object_or_404(
        DailyExam,
        pk=exam_id,
        exam_date=today,
        is_published=True,
    )

    existing = ExamAttempt.objects.filter(
        daily_exam=daily_exam,
        student=request.user,
    ).first()

    if existing:
        if existing.is_submitted or now >= existing.deadline_at:
            finalize_attempt(existing.pk)
            return redirect("exam-result", attempt_id=existing.pk)
        return redirect("take-exam", attempt_id=existing.pk)

    try:
        with transaction.atomic():
            existing = ExamAttempt.objects.filter(
                daily_exam=daily_exam,
                student=request.user,
            ).first()

            if existing:
                attempt = existing
            else:
                attempt = ExamAttempt.objects.create(
                    daily_exam=daily_exam,
                    student=request.user,
                    started_at=now,
                    deadline_at=now + timedelta(
                        minutes=daily_exam.duration_minutes
                    ),
                )
    except IntegrityError:
        attempt = ExamAttempt.objects.get(
            daily_exam=daily_exam,
            student=request.user,
        )

    if attempt.is_submitted or now >= attempt.deadline_at:
        finalize_attempt(attempt.pk)
        return redirect("exam-result", attempt_id=attempt.pk)

    messages.info(
        request,
        "Your timer has started. Your answers are saved as you work.",
    )
    return redirect("take-exam", attempt_id=attempt.pk)


@login_required
def take_exam(request, attempt_id):
    if request.user.is_staff:
        return redirect("admin:index")

    attempt = get_object_or_404(
        ExamAttempt.objects.select_related("daily_exam"),
        pk=attempt_id,
        student=request.user,
    )

    if attempt.is_submitted:
        return redirect("exam-result", attempt_id=attempt.pk)

    if timezone.now() >= attempt.deadline_at:
        finalize_attempt(attempt.pk)
        return redirect("exam-result", attempt_id=attempt.pk)

    saved_answers = {
        answer.question_id: answer.selected_option_id
        for answer in StudentAnswer.objects.filter(attempt=attempt)
    }

    # Deliberately pass dictionaries containing only student-visible fields.
    questions = []
    for question in attempt.daily_exam.questions.prefetch_related("options"):
        questions.append({
            "id": question.pk,
            "text": question.question_text,
            "image_url": cloudinary_asset_url(question.image_url),
            "audio_url": cloudinary_asset_url(question.audio_url, "video"),
            "order": question.order,
            "options": [
                {
                    "id": option.pk,
                    "text": option.option_text,
                    "image_url": cloudinary_asset_url(option.image_url),
                    "audio_url": cloudinary_asset_url(option.audio_url, "video"),
                }
                for option in question.options.all()
            ],
        })

    return render(
        request,
        "exams/take_exam.html",
        {
            "attempt": attempt,
            "questions": questions,
            "saved_answers": saved_answers,
            "server_now_ms": int(timezone.now().timestamp() * 1000),
            "deadline_ms": int(attempt.deadline_at.timestamp() * 1000),
        },
    )


@login_required
@require_POST
def save_answer(request, attempt_id):
    if request.user.is_staff:
        return JsonResponse({"error": "Not allowed."}, status=403)

    attempt = get_object_or_404(
        ExamAttempt,
        pk=attempt_id,
        student=request.user,
    )

    if attempt.is_submitted:
        return JsonResponse({"error": "This exam is already submitted."}, status=409)

    if timezone.now() >= attempt.deadline_at:
        finalize_attempt(attempt.pk)
        return JsonResponse(
            {"error": "Time is over. Your exam has been submitted."},
            status=409,
        )

    try:
        data = json.loads(request.body)
        question_id = int(data["question_id"])
        option_value = data.get("option_id")
        option_id = int(option_value) if option_value not in (None, "") else None
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid answer data."}, status=400)

    from exams.models import ExamQuestion, ExamOption

    question = get_object_or_404(
        ExamQuestion,
        pk=question_id,
        daily_exam_id=attempt.daily_exam_id,
    )

    if option_id is None:
        StudentAnswer.objects.filter(
            attempt=attempt,
            question=question,
        ).delete()
        return JsonResponse({"saved": True})

    option = get_object_or_404(
        ExamOption,
        pk=option_id,
        question_id=question.pk,
    )

    StudentAnswer.objects.update_or_create(
        attempt=attempt,
        question=question,
        defaults={"selected_option": option},
    )

    return JsonResponse({"saved": True})


@login_required
def exam_instructions(request, exam_id):
    if request.user.is_staff:
        return redirect("admin:index")

    daily_exam = get_object_or_404(
        DailyExam,
        pk=exam_id,
        exam_date=timezone.localdate(),
        is_published=True,
    )

    existing = ExamAttempt.objects.filter(
        daily_exam=daily_exam,
        student=request.user,
    ).first()

    if existing:
        if existing.is_submitted:
            return redirect("exam-result", attempt_id=existing.pk)

        if timezone.now() >= existing.deadline_at:
            finalize_attempt(existing.pk)
            return redirect("exam-result", attempt_id=existing.pk)

        return redirect("take-exam", attempt_id=existing.pk)

    return render(
        request,
        "exams/instructions.html",
        {"daily_exam": daily_exam},
    )


@login_required
@require_POST
def submit_exam(request, attempt_id):
    if request.user.is_staff:
        return redirect("admin:index")

    attempt = get_object_or_404(
        ExamAttempt,
        pk=attempt_id,
        student=request.user,
    )

    finalize_attempt(attempt.pk)
    return redirect("exam-result", attempt_id=attempt.pk)


@login_required

@login_required
def exam_result(request, attempt_id):
    if request.user.is_staff:
        return redirect("admin:index")

    attempt = get_object_or_404(
        ExamAttempt.objects.select_related("daily_exam"),
        pk=attempt_id,
        student=request.user,
    )

    if not attempt.is_submitted:
        if timezone.now() >= attempt.deadline_at:
            attempt = finalize_attempt(attempt.pk)
        else:
            return redirect("take-exam", attempt_id=attempt.pk)

    # Result statistics only; never expose answers or explanations.
    total_questions = attempt.daily_exam.questions.count()

    attempted_count = StudentAnswer.objects.filter(
        attempt=attempt,
        selected_option__isnull=False,
    ).count()

    correct_count = attempt.correct_answers
    incorrect_count = max(0, attempted_count - correct_count)
    skipped_count = max(0, total_questions - attempted_count)

    percentage = max(0.0, min(100.0, float(attempt.percentage)))

    if percentage >= 90:
        performance = "Outstanding"
    elif percentage >= 75:
        performance = "Excellent"
    elif percentage >= 60:
        performance = "Good"
    elif percentage >= 40:
        performance = "Needs Improvement"
    else:
        performance = "Keep Practicing"

    # Build an overall leaderboard using the best submitted attempt
    # for each student.
    all_attempts = (
        ExamAttempt.objects
        .filter(is_submitted=True)
        .select_related("student", "daily_exam")
        .order_by(
            "-percentage",
            "-score",
            "duration_seconds",
            "submitted_at",
            "pk",
        )
    )

    best_attempts = []
    seen_students = set()

    for result_attempt in all_attempts:
        if result_attempt.student_id in seen_students:
            continue

        seen_students.add(result_attempt.student_id)
        best_attempts.append(result_attempt)

    leaderboard = best_attempts[:10]
    current_student_rank = None

    for rank, result_attempt in enumerate(best_attempts, start=1):
        result_attempt.leaderboard_rank = rank

        if result_attempt.student_id == request.user.pk:
            current_student_rank = rank

        if rank <= 10:
            result_attempt.leaderboard_name = (
                result_attempt.student.get_full_name().strip()
                or result_attempt.student.username
            )
            result_attempt.leaderboard_percentage = float(
                result_attempt.percentage
            )

    return render(
        request,
        "results/result.html",
        {
            "attempt": attempt,
            "total_questions": total_questions,
            "attempted_count": attempted_count,
            "correct_count": correct_count,
            "incorrect_count": incorrect_count,
            "skipped_count": skipped_count,
            "percentage": percentage,
            "performance": performance,
            "leaderboard": leaderboard,
            "current_student_rank": current_student_rank,
        },
    )

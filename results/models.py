
from django.conf import settings
from django.db import models
from django.db.models import Q


class ExamAttempt(models.Model):
    daily_exam = models.ForeignKey(
        "exams.DailyExam",
        on_delete=models.PROTECT,
        related_name="attempts",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="exam_attempts",
    )

    started_at = models.DateTimeField()
    deadline_at = models.DateTimeField()
    submitted_at = models.DateTimeField(null=True, blank=True)

    is_submitted = models.BooleanField(default=False)
    correct_answers = models.PositiveIntegerField(default=0)
    score = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["daily_exam", "student"],
                name="one_attempt_per_student_per_exam",
            ),
            models.CheckConstraint(
                condition=Q(deadline_at__gte=models.F("started_at")),
                name="attempt_deadline_after_start",
            ),
        ]
        indexes = [
            models.Index(fields=["daily_exam", "is_submitted"]),
            models.Index(fields=["student", "is_submitted"]),
            models.Index(fields=["-score", "duration_seconds"]),
        ]
        ordering = ["-score", "duration_seconds"]

    def __str__(self):
        return f"{self.student} - {self.daily_exam}"


class StudentAnswer(models.Model):
    attempt = models.ForeignKey(
        ExamAttempt,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        "exams.ExamQuestion",
        on_delete=models.PROTECT,
        related_name="student_answers",
    )
    selected_option = models.ForeignKey(
        "exams.ExamOption",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="selected_by",
    )
    answered_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="one_answer_per_question_per_attempt",
            ),
        ]
        indexes = [
            models.Index(fields=["attempt", "question"]),
        ]

    def __str__(self):
        return f"Attempt {self.attempt_id} - Question {self.question_id}"

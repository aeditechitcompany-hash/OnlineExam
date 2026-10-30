
from django.conf import settings
from django.db import models


class DailyExam(models.Model):
    title = models.CharField(max_length=200)
    exam_date = models.DateField(db_index=True)
    duration_minutes = models.PositiveSmallIntegerField(default=50)
    total_questions = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    source_set_id = models.CharField(max_length=100, blank=True, db_index=True)
    source_category = models.CharField(max_length=100, blank=True)
    source_description = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_daily_exams",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-exam_date"]
        indexes = [
            models.Index(fields=["exam_date", "is_published"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.exam_date}"


class ExamQuestion(models.Model):
    daily_exam = models.ForeignKey(
        DailyExam,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    source_question_id = models.CharField(max_length=100, blank=True)
    question_type = models.CharField(max_length=30, default="text")
    question_text = models.TextField(blank=True)
    image_url = models.CharField(max_length=1000, blank=True)
    audio_url = models.CharField(max_length=1000, blank=True)
    explanation = models.TextField(blank=True)
    points = models.PositiveSmallIntegerField(default=1)
    section_name = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        indexes = [
            models.Index(fields=["daily_exam", "order"]),
        ]

    def __str__(self):
        return f"Question {self.order} - {self.daily_exam}"


class ExamOption(models.Model):
    question = models.ForeignKey(
        ExamQuestion,
        on_delete=models.CASCADE,
        related_name="options",
    )
    option_text = models.TextField(blank=True)
    image_url = models.CharField(max_length=1000, blank=True)
    audio_url = models.CharField(max_length=1000, blank=True)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        indexes = [
            models.Index(fields=["question", "order"]),
        ]

    def __str__(self):
        return f"Option {self.order} for question {self.question_id}"

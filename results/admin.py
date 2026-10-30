
from django.contrib import admin
from .models import ExamAttempt, StudentAnswer


class StudentAnswerInline(admin.TabularInline):
    model = StudentAnswer
    extra = 0
    readonly_fields = ("answered_at",)


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "daily_exam",
        "started_at",
        "submitted_at",
        "is_submitted",
        "correct_answers",
        "score",
        "percentage",
        "duration_seconds",
    )
    list_filter = ("daily_exam", "is_submitted")
    search_fields = (
        "student__username",
        "student__first_name",
        "student__last_name",
        "student__phone_number",
    )
    readonly_fields = (
        "started_at",
        "deadline_at",
        "submitted_at",
        "correct_answers",
        "score",
        "percentage",
        "duration_seconds",
    )
    inlines = [StudentAnswerInline]


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = (
        "attempt",
        "question",
        "selected_option",
        "answered_at",
    )
    list_filter = ("attempt__daily_exam",)
    search_fields = ("attempt__student__username",)

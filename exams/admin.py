
from django.contrib import admin
from .models import DailyExam, ExamQuestion, ExamOption


class ExamOptionInline(admin.TabularInline):
    model = ExamOption
    extra = 0


@admin.register(ExamQuestion)
class ExamQuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "daily_exam", "order", "question_text")
    list_filter = ("daily_exam",)
    search_fields = ("question_text",)
    inlines = [ExamOptionInline]


@admin.register(DailyExam)
class DailyExamAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "exam_date",
        "duration_minutes",
        "total_questions",
        "is_published",
    )
    list_filter = ("is_published", "exam_date")
    search_fields = ("title",)
    ordering = ("-exam_date",)

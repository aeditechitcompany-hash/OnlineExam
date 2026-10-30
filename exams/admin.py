
from datetime import date
from io import StringIO

from django.contrib import admin, messages
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connections, DatabaseError
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils import timezone

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
    change_list_template = "admin/exams/dailyexam/change_list.html"

    def get_urls(self):
        custom_urls = [
            path(
                "import-question-set/",
                self.admin_site.admin_view(self.import_question_set_view),
                name="exams_dailyexam_import_question_set",
            ),
        ]
        return custom_urls + super().get_urls()

    def import_question_set_view(self, request):
        opts = self.model._meta
        context = {
            **self.admin_site.each_context(request),
            "opts": opts,
            "title": "Import Question Set",
            "exam_date": timezone.localdate().isoformat(),
            "duration": 50,
            "question_sets": [],
        }

        # Read active source sets without modifying the source database.
        try:
            with connections["source_mcq"].cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, title, description, category
                    FROM mcq_questionset
                    WHERE is_active = TRUE
                    ORDER BY title, id
                    """
                )
                context["question_sets"] = [
                    {
                        "id": str(row[0]),
                        "title": row[1],
                        "description": row[2] or "",
                        "category": row[3] or "",
                    }
                    for row in cursor.fetchall()
                ]
        except DatabaseError:
            import logging
            logging.getLogger(__name__).exception(
                "Failed to load MCQ question sets from source_mcq"
            )
            messages.error(
                request,
                "Could not load source question sets. "
                "Check the Render logs for the database error.",
            )
            return render(
                request,
                "admin/exams/dailyexam/import_question_sets.html",
                context,
            )

        if request.method == "POST":
            source_set_id = request.POST.get("source_set_id", "").strip()
            exam_date_text = request.POST.get("exam_date", "").strip()
            duration_text = request.POST.get("duration", "").strip()

            try:
                # Only allow a set shown in the active source-set list.
                if not any(
                    item["id"] == source_set_id
                    for item in context["question_sets"]
                ):
                    raise ValueError("Select a valid active question set.")

                exam_date = date.fromisoformat(exam_date_text)
                duration = int(duration_text)

                if not 1 <= duration <= 300:
                    raise ValueError(
                        "Duration must be between 1 and 300 minutes."
                    )

                output = StringIO()
                call_command(
                    "import_question_set",
                    source_set_id,
                    date=exam_date,
                    duration=duration,
                    created_by=request.user.pk,
                    stdout=output,
                )

                messages.success(request, output.getvalue())
                return redirect(
                    reverse("admin:exams_dailyexam_changelist")
                )

            except (ValueError, CommandError) as exc:
                messages.error(request, str(exc))
                context["exam_date"] = exam_date_text
                context["duration"] = duration_text

        return render(
            request,
            "admin/exams/dailyexam/import_question_sets.html",
            context,
        )


from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path

from accounts.views import ExamLoginView, register
from exams.views import (
    exam_home,
    exam_instructions,
    exam_result,
    save_answer,
    start_exam,
    submit_exam,
    take_exam,
)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", ExamLoginView.as_view(), name="login"),
    path("accounts/register/", register, name="register"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("", exam_home, name="exam-home"),
    path(
        "exams/<int:exam_id>/instructions/",
        exam_instructions,
        name="exam-instructions",
    ),
    path("exams/<int:exam_id>/start/", start_exam, name="start-exam"),
    path("exams/attempt/<int:attempt_id>/", take_exam, name="take-exam"),
    path(
        "exams/attempt/<int:attempt_id>/save/",
        save_answer,
        name="save-answer",
    ),
    path(
        "exams/attempt/<int:attempt_id>/submit/",
        submit_exam,
        name="submit-exam",
    ),
    path(
        "exams/attempt/<int:attempt_id>/result/",
        exam_result,
        name="exam-result",
    ),
]

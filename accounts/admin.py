from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import ExamUser


@admin.register(ExamUser)
class ExamUserAdmin(UserAdmin):
    list_display = (
        "username",
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "is_active",
        "is_staff",
    )

    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "phone_number",
    )

    fieldsets = UserAdmin.fieldsets + (
        ("Exam Contact Details", {"fields": ("phone_number",)}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Exam Contact Details", {"fields": ("phone_number",)}),
    )
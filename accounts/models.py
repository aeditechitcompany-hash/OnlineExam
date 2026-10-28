from django.contrib.auth.models import AbstractUser
from django.db import models


class ExamUser(AbstractUser):
    phone_number = models.CharField(max_length=20, blank=True, db_index=True)

    class Meta:
        verbose_name = "Exam User"
        verbose_name_plural = "Exam Users"

    def __str__(self):
        return self.get_full_name() or self.username
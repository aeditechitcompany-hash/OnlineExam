from django.shortcuts import render

# Create your views here.

from django import forms
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse

from .models import ExamUser


class ExamRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone_number = forms.CharField(max_length=20)

    class Meta:
        model = ExamUser
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if ExamUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email


class ExamLoginView(LoginView):
    template_name = "accounts/login.html"

    def get_success_url(self):
        if self.request.user.is_staff:
            return reverse("admin:index")
        return reverse("exam-home")


def register(request):
    if request.user.is_authenticated:
        from django.contrib.auth import logout
        logout(request)
        
    if request.method == "POST":
        form = ExamRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Your account was created successfully.")
            return redirect("exam-home")
    else:
        form = ExamRegistrationForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form},
    )

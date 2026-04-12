from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import ValidationError, validate_password
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import render

from .models import NeueUser


def login_view(req):
    if req.user.is_authenticated:
        return HttpResponseRedirect("/")
    elif req.method == "GET":
        return render(req, "neue_accounts/login.html")
    elif req.method == "POST":
        email = req.POST.get("email", "").strip()
        password = req.POST.get("password", "").strip()

        errors = []

        if not email:
            errors.append("Email is required.")
        if not password:
            errors.append("Password is required.")

        try:
            validate_password(password)
        except ValidationError as e:
            for error in e:
                errors.append(f"Password invalid: {error}")

        try:
            user = authenticate(req, username=email, password=password)

            if user is not None:
                login(req, user)
                return HttpResponseRedirect("/")
            else:
                errors.append("Invalid email or password.")
                return render(req, "neue_accounts/login.html", {"errors": errors})
        except Exception as e:
            errors.append("User not found")
            return render(req, "neue_accounts/login.html", {"errors": errors})


def register_view(req):
    if req.user.is_authenticated:
        return HttpResponseRedirect("/")
    elif req.method == "GET":
        return render(req, "neue_accounts/register.html")
    elif req.method == "POST":
        email = req.POST.get("email", "").strip()
        password = req.POST.get("password", "").strip()
        confirm_password = req.POST.get("confirmPassword", "").strip()

        # Validate inputs
        errors = []

        if not email:
            errors.append("Email is required.")
        if not password:
            errors.append("Password is required.")
        if not confirm_password:
            errors.append("Password confirmation is required.")

        # Check password match
        if password and confirm_password and password != confirm_password:
            errors.append("Passwords do not match.")

        # Validate the password against AUTH_PASSWORD_VALIDATORS
        try:
            validate_password(password)
        except ValidationError as e:
            for error in e:
                errors.append(f"Password invalid: {error}")

        if errors:
            return render(
                req,
                "neue_accounts/register.html",
                {"errors": errors, "email": email},
            )

        try:
            user = NeueUser.objects.create_user(email=email, password=password)
            login(req, user)
            return HttpResponseRedirect("/")
        except IntegrityError:
            errors.append("An account with this email already exists.")
            return render(
                req,
                "neue_accounts/register.html",
                {"errors": errors, "email": email},
            )
        except Exception as e:
            print(e)
            errors.append("An error occurred during registration. Please try again.")
            return render(
                req,
                "neue_accounts/register.html",
                {"errors": errors, "email": email},
            )


def logout_view(req):
    try:
        logout(req)
    except Exception:
        return HttpResponseRedirect("/")
    else:
        return HttpResponseRedirect("/accounts/login")

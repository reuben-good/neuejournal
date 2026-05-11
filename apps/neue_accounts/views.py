from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import ValidationError, validate_password
from django.contrib.sites.shortcuts import get_current_site
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from apps.helpers.email import AccountActivationTokenGenerator, send_email

from .models import NeueUser


def login_view(req):
    # If a user is authenticated, they should access the home page and logout from there
    if req.user.is_authenticated:
        return HttpResponseRedirect("/")
    elif req.method == "GET":
        # When a GET request is made, render the login form
        return render(req, "neue_accounts/login.html")
    elif req.method == "POST":
        # When a POST request is made, extract the email and password
        email = req.POST.get("email", "").strip()
        password = req.POST.get("password", "").strip()

        # Create an array for keeping track of errors
        errors = []

        if not email:
            errors.append("Email is required.")
        if not password:
            errors.append("Password is required.")

        try:
            validate_password(password)  # Django's built-in password validators
        except ValidationError as e:
            for error in e:
                errors.append(f"Password invalid: {error}")

        try:
            # Try to authenticate the user and gracefully handle errors if they occur
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


token_generator = AccountActivationTokenGenerator()


def register_view(req):
    # If a user is authenticated, they should access the home page and logout from there
    if req.user.is_authenticated:
        return HttpResponseRedirect("/")
    elif req.method == "GET":
        # When a GET request is made, render the login form
        return render(req, "neue_accounts/register.html")
    elif req.method == "POST":
        # When a POST request is made, extract the email and password
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
            user.is_active = False
            user.save()

            domain = get_current_site(req).domain
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = token_generator.make_token(user)
            send_email(
                subject="Please confirm your email",
                text_content=f"Verify your email at: http://{domain}/auth/activate/{uid}/{token}",
                html_content=render_to_string(
                    "neue_accounts/emails/account_activation_email.html",
                    {
                        "domain": domain,
                        "uid": uid,
                        "token": token,
                    },
                ),
                address=email,
            )
            return HttpResponseRedirect(
                reverse(
                    "neue_accounts:verify_message",
                    kwargs={"uidb64": urlsafe_base64_encode(force_bytes(user.pk))},
                )
            )
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


def verify_message_view(req, uidb64):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = NeueUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError):
        user = None

    if user is not None:
        return render(req, "neue_accounts/verify_message.html", {"email": user.email})
    else:
        return render(
            req,
            "neue_accounts/register.html",
            {"errors": ["There was an issue sending our verification email"]},
        )


def activate(req, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = NeueUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError):
        user = None

    if user is not None and token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(req, user)
        return HttpResponseRedirect("/")
    else:
        return render(
            req,
            "neue_accounts/register.html",
            {"errors": ["There was an issue verifying your email"]},
        )


@login_required(login_url="/auth/login")
def logout_view(req):
    if req.method != "POST":
        return HttpResponseBadRequest(
            "This route is POST only for CSRF protection".encode()
        )

    try:
        logout(req)
    except Exception:
        return HttpResponseRedirect("/")
    else:
        return HttpResponseRedirect("/auth/login")


@login_required(login_url="/auth/login")
def delete_view(req):
    if req.method != "POST":
        return HttpResponseBadRequest(
            "This route is POST only for CSRF protection".encode()
        )

    try:
        req.user.delete()
    except Exception as e:
        print("Couldn't delete user: ", e)
        return HttpResponse(status=404, content=f"Couldn't delete user: {e}".encode())
    else:
        return HttpResponseRedirect("/")

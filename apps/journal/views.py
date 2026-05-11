from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import (
    FileResponse,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from apps.helpers.email import send_email
from apps.helpers.encryption import decrypt_with_key, encrypt_with_key

from .models import Entry, JournalSettings, Photo


# Create your views here.
def home_view(req):
    if req.user.is_authenticated:
        settingsObject = JournalSettings.objects.filter(owner=req.user).first()
        try:
            colour = settingsObject.colour
        except Exception:
            colour = JournalSettings(
                owner=req.user,
            )
            colour.save()
            colour = colour.colour
        return render(req, "journal/journal.html", {"colour": colour})
    else:
        return render(req, "journal/landing.html")


MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


@login_required(login_url="/auth/login")
def create_entry(req):
    if req.method != "POST":
        return HttpResponse(status=405)

    content = req.POST.get("content", "").strip()
    entry_type = req.POST.get("entry_type", "").strip()

    if not content or not entry_type:
        return HttpResponse(content="Must have content".encode(), status=400)

    files = req.FILES.getlist("images")

    if len(files) > 3:
        return HttpResponse(content="Maximum 3 images allowed".encode(), status=400)

    for f in files:
        if f.size > MAX_IMAGE_SIZE:
            return HttpResponse(
                content=f'"{f.name}" exceeds the 5MB limit ({f.size / 1024 / 1024:.1f}MB)'.encode(),
                status=400,
            )

    # All validation passed
    try:
        entry = Entry(
            owner=req.user,
            content=encrypt_with_key(key=req.user.user_key, data=content.encode()),
            type=entry_type,
            date=datetime.today(),
        )
        entry.save()

        for f in files:
            Photo(entry=entry, image=f).save()

    except ValidationError as e:
        return HttpResponse(content=str(e).encode(), status=400)
    except Exception as e:
        return HttpResponse(content=str(e).encode(), status=503)

    return HttpResponse(status=200)


@login_required(login_url="/auth/login")
def serve_photo(req, photo_id):
    """Serve a photo from S3 storage through Django to avoid CORS issues"""
    try:
        photo = Photo.objects.get(id=photo_id, entry__owner=req.user)
        photo_file = photo.image.open("rb")
        response = FileResponse(photo_file, content_type="image/jpeg")
        response["Content-Disposition"] = 'inline; filename="photo"'
        return response
    except Photo.DoesNotExist:
        return HttpResponse(status=404)
    except Exception as e:
        return HttpResponse(status=500)


def serve_photo_with_token(req, photo_id, token):
    """Serve a photo using a time-limited token for email access.

    This endpoint allows unauthenticated access to photos via a token,
    enabling images to load in emails without requiring user login.
    """
    try:
        photo = Photo.objects.get(id=photo_id)

        # Verify token exists and matches
        if not photo.email_token or photo.email_token != token:
            return HttpResponse(status=403)

        # Check if token has expired
        if photo.email_token_expires and timezone.now() > photo.email_token_expires:
            return HttpResponse(status=403)  # Token expired

        photo_file = photo.image.open("rb")
        response = FileResponse(photo_file, content_type="image/jpeg")
        response["Content-Disposition"] = 'inline; filename="photo"'
        return response
    except Photo.DoesNotExist:
        return HttpResponse(status=404)
    except Exception as e:
        return HttpResponse(status=500)


ENTRIES_PER_PAGE = 5


@login_required(login_url="/auth/login")
def fetch_entry_months(req):
    """Return every (year, month) pair the user has entries for, excluding
    the current calendar month, ordered newest first.

    The front-end uses this to know which months to render in the journal
    without having to hard-code anything.
    """
    if req.method != "GET":
        return HttpResponse(status=405)

    try:
        today = datetime.today()

        # Pull just the dates we need so we can build the (year, month) set
        # in Python without depending on a particular DB backend's date
        # truncation functions.
        dates = (
            Entry.objects.filter(owner=req.user)
            .exclude(date__year=today.year, date__month=today.month)
            .values_list("date", flat=True)
        )

        seen = set()
        for d in dates:
            seen.add((d.year, d.month))

        months = [{"year": y, "month": m} for (y, m) in sorted(seen, reverse=True)]

        return JsonResponse({"months": months})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=503)


def _get_entries_for_month(user, year, month):
    """Return queryset of entries for the given user/year/month, excluding the
    current calendar month, newest first."""
    today = datetime.today()
    return (
        Entry.objects.filter(owner=user, date__year=year, date__month=month)
        .exclude(date__year=today.year, date__month=today.month)
        .order_by("-date")
    )


@login_required(login_url="/auth/login")
def fetch_entry_list_meta(req, year, month):
    """Return metadata about how many pages of entries exist for a given month.

    Used by the front-end so it can dynamically build the right number of
    page pairs in the journal.
    """
    if req.method != "GET":
        return HttpResponse(status=405)

    try:
        total_entries = _get_entries_for_month(req.user, year, month).count()
        # ceil division
        total_pages = (total_entries + ENTRIES_PER_PAGE - 1) // ENTRIES_PER_PAGE
        return JsonResponse(
            {
                "year": int(year),
                "month": int(month),
                "total_entries": total_entries,
                "total_pages": total_pages,
                "entries_per_page": ENTRIES_PER_PAGE,
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=503)


@login_required(login_url="/auth/login")
def fetch_entry_list(req, year, month, page=1):
    """Render a single window of up to ENTRIES_PER_PAGE entries for the given
    month. ``page`` is 1-indexed."""
    if req.method != "GET":
        return HttpResponse(status=405)

    try:
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = 1
        if page < 1:
            page = 1

        entries_qs = _get_entries_for_month(req.user, year, month)
        total_entries = entries_qs.count()

        if total_entries == 0:
            return render(
                req,
                "journal/pages/entry-list.html",
                {
                    "month": None,
                    "entries": [],
                    "total_entries": 0,
                    "page": page,
                    "total_pages": 0,
                },
            )

        total_pages = (total_entries + ENTRIES_PER_PAGE - 1) // ENTRIES_PER_PAGE

        # Slice the queryset to just this window.
        start = (page - 1) * ENTRIES_PER_PAGE
        end = start + ENTRIES_PER_PAGE
        window_entries = list(entries_qs[start:end])

        # Determine the human-readable month label from the first entry in
        # the window (falls back to the requested year/month if the window is
        # empty, e.g. an out-of-range page).
        if window_entries:
            month_label = window_entries[0].date.strftime("%B %Y")
        else:
            try:
                month_label = datetime(int(year), int(month), 1).strftime("%B %Y")
            except ValueError:
                month_label = ""

        rendered_entries = []
        for entry in window_entries:
            photos = Photo.objects.filter(entry=entry)
            image_urls = [
                reverse("journal:serve-photo", args=[photo.id]) for photo in photos
            ]
            decrypted_content = decrypt_with_key(
                key=req.user.user_key, encrypted=entry.content
            ).decode("utf-8")

            rendered_entries.append(
                {
                    "id": entry.id,
                    "date": entry.date.isoformat(),
                    "content": decrypted_content,
                    "type": entry.type,
                    "image_urls": image_urls,
                }
            )

        return render(
            req,
            "journal/pages/entry-list.html",
            {
                "month": month_label,
                "entries": rendered_entries,
                "total_entries": total_entries,
                "page": page,
                "total_pages": total_pages,
            },
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=503)


@login_required(login_url="/auth/login")
def fetch_entry_detail(req, entry_id):
    if req.method != "GET":
        return HttpResponse(status=405)

    try:
        # Get the entry, ensuring it belongs to the current user
        entry = Entry.objects.get(id=entry_id, owner=req.user)

        # Get photos for this entry
        photos = Photo.objects.filter(entry=entry)
        image_urls = [
            reverse("journal:serve-photo", args=[photo.id]) for photo in photos
        ]

        # Decrypt content
        decrypted_content = decrypt_with_key(
            key=req.user.user_key, encrypted=entry.content
        ).decode("utf-8")

        # Format the date
        date_obj = entry.date
        days = [
            "Sunday",
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
        ]
        months = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]

        def get_ordinal_suffix(num):
            integer = int(num)
            mod100 = integer % 100
            if mod100 >= 11 and mod100 <= 13:
                return "th"
            mod10 = integer % 10
            if mod10 == 1:
                return "st"
            elif mod10 == 2:
                return "nd"
            elif mod10 == 3:
                return "rd"
            else:
                return "th"

        date_display = f"{days[date_obj.weekday() + 1 if date_obj.weekday() < 6 else 0]}, {date_obj.day}{get_ordinal_suffix(date_obj.day)}"

        return render(
            req,
            "journal/pages/entry-detail.html",
            {
                "entry": {
                    "id": entry.id,
                    "content": decrypted_content,
                    "type": entry.type,
                    "image_urls": image_urls,
                    "month": months[date_obj.month - 1],
                    "year": date_obj.year,
                    "date_display": date_display,
                }
            },
        )

    except Entry.DoesNotExist:
        return HttpResponse(status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=503)


@login_required(login_url="/auth/login")
def fetch_entry_images(req, entry_id):
    if req.method != "GET":
        return HttpResponse(status=405)

    try:
        # Get the entry, ensuring it belongs to the current user
        entry = Entry.objects.get(id=entry_id, owner=req.user)

        # Get photos for this entry
        photos = Photo.objects.filter(entry=entry)
        image_urls = [
            reverse("journal:serve-photo", args=[photo.id]) for photo in photos
        ]

        return render(req, "journal/pages/entry-images.html", {"urls": image_urls})
    except Exception as e:
        print(e)
        return HttpResponse(status=404, content=str(e).encode())


@login_required(login_url="/auth/login")
def empty_page(req):
    # This will be a customisable sticker page soon!
    return render(req, "journal/pages/empty-page.html")


@login_required(login_url="/auth/login")
def account_panel(req):
    if not req.headers.get("X-Requested-With") == "XMLHttpRequest":
        return HttpResponseBadRequest("Panel endpoint only.".encode())

    return render(req, "journal/components/navpanels/account.html", {"user": req.user})


@login_required(login_url="/auth/login")
def journal_panel(req):
    if not req.headers.get("X-Requested-With") == "XMLHttpRequest":
        return HttpResponseBadRequest("Panel endpoint only.".encode())

    settingsObject = JournalSettings.objects.filter(owner=req.user).first()
    return render(
        req,
        "journal/components/navpanels/journal.html",
        {"colour": settingsObject.colour},
    )


@login_required(login_url="/auth/login")
def journal_settings(req):
    if req.method != "POST":
        return HttpResponseBadRequest("POST endpoint only".encode())

    try:
        colour = req.POST.get("colour", "").strip().replace("#", "")

        settings = JournalSettings.objects.filter(owner=req.user).first()
        settings.colour = colour

        settings.save()
    except Exception as e:
        print(e)
        return HttpResponse(status=500, content=str(e).encode())
    else:
        return HttpResponseRedirect("/")

from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import (
    FileResponse,
    HttpResponse,
    JsonResponse,
)
from django.shortcuts import render
from django.urls import reverse

from apps.helpers.encryption import decrypt_with_key, encrypt_with_key

from .models import Entry, Photo


# Create your views here.
def home_view(req):
    if req.user.is_authenticated:
        return render(req, "journal/journal.html")
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


@login_required(login_url="/auth/login")
def fetch_entry_list(req, year, month):
    if req.method != "GET":
        return HttpResponse(status=405)

    try:
        # Get current month
        today = datetime.today()

        # Get all entries NOT from this month, ordered by date (newest first) only from this year
        entries = (
            Entry.objects.filter(owner=req.user, date__year=year, date__month=month)
            .exclude(date__year=today.year, date__month=today.month)
            .order_by("-date")
        )

        if not entries:
            return render(
                req,
                "journal/pages/entry-list.html",
                {"entries": [], "total_entries": 0},
            )

        # Group entries by month
        entries_by_month = {}
        for entry in entries:
            month_key = entry.date.strftime("%Y-%m")
            month_label = entry.date.strftime("%B %Y")

            if month_key not in entries_by_month:
                entries_by_month[month_key] = {"label": month_label, "entries": []}

            entries_by_month[month_key]["entries"].append(entry)

        # Create pages (5 entries per page, grouped by month)
        pages_data = []
        ENTRIES_PER_PAGE = 5

        for month_key in sorted(entries_by_month.keys(), reverse=True):
            month_info = entries_by_month[month_key]
            month_entries = month_info["entries"]
            month_label = month_info["label"]

            # Split month's entries into pages
            for i in range(0, len(month_entries), ENTRIES_PER_PAGE):
                page_entries = month_entries[i : i + ENTRIES_PER_PAGE]
                page_data = {"month": month_label, "entries": []}

                for entry in page_entries:
                    # Get photos for this entry
                    photos = Photo.objects.filter(entry=entry)
                    # Generate proxy URLs through Django instead of direct S3 URLs
                    # This avoids CORS issues with the browser
                    image_urls = [
                        reverse("journal:serve-photo", args=[photo.id])
                        for photo in photos
                    ]
                    # Decrypt content
                    decrypted_content = decrypt_with_key(
                        key=req.user.user_key, encrypted=entry.content
                    ).decode("utf-8")

                    page_data["entries"].append(
                        {
                            "id": entry.id,
                            "date": entry.date.isoformat(),
                            "content": decrypted_content,
                            "type": entry.type,
                            "image_urls": image_urls,
                        }
                    )

                pages_data.append(page_data)

        total_entries = len(entries)
        return render(
            req,
            "journal/pages/entry-list.html",
            {
                "entries": pages_data,
                "total_entries": total_entries,
                "total_pages": len(pages_data),
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

import json
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
from django.urls import reverse
from django.utils import timezone

from apps.helpers.encryption import decrypt_with_key, encrypt_with_key

from .models import Entry, JournalSettings, OwnedPack, Photo, Sticker, StickerPosition


def home_view(req):
    if not req.user.is_authenticated:
        return render(req, "journal/landing.html")

    settings = JournalSettings.objects.filter(owner=req.user).first()

    # No settings row yet → brand new user, start at step 0
    if settings is None:
        return HttpResponseRedirect("/onboarding/0")

    # Settings exist but name is blank → didn't finish onboarding
    # Resume at whichever step they left off at.
    if not settings.belongs_to:
        # colour is set means they completed step 0; send them to step 1
        if settings.colour != JournalSettings._meta.get_field("colour").default:
            return HttpResponseRedirect("/onboarding/1")
        return HttpResponseRedirect("/onboarding/0")

    # Fully onboarded
    return render(req, "journal/journal.html", {"colour": settings.colour})


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
    except Exception:
        return HttpResponse(status=500)


def serve_photo_with_token(req, photo_id, token):
    """Serve a photo using a time-limited token for email access."""
    try:
        photo = Photo.objects.get(id=photo_id)

        if not photo.email_token or photo.email_token != token:
            return HttpResponse(status=403)

        if photo.email_token_expires and timezone.now() > photo.email_token_expires:
            return HttpResponse(status=403)

        photo_file = photo.image.open("rb")
        response = FileResponse(photo_file, content_type="image/jpeg")
        response["Content-Disposition"] = 'inline; filename="photo"'
        return response
    except Photo.DoesNotExist:
        return HttpResponse(status=404)
    except Exception:
        return HttpResponse(status=500)


@login_required(login_url="/auth/login")
def serve_sticker(req, sticker_id):
    """Serve a sticker from S3 sticker storage through Django"""
    try:
        sticker = Sticker.objects.get(id=sticker_id)
        sticker_file = sticker.image.open("rb")
        response = FileResponse(sticker_file, content_type="image/png")
        response["Content-Disposition"] = 'inline; filename="sticker"'
        return response
    except Sticker.DoesNotExist:
        return HttpResponse(status=404)
    except Exception:
        return HttpResponse(status=500)


ENTRIES_PER_PAGE = 5


@login_required(login_url="/auth/login")
def fetch_entry_months(req):
    if req.method != "GET":
        return HttpResponse(status=405)

    try:
        today = datetime.today()
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
    today = datetime.today()
    return (
        Entry.objects.filter(owner=user, date__year=year, date__month=month)
        .exclude(date__year=today.year, date__month=today.month)
        .order_by("-date")
    )


@login_required(login_url="/auth/login")
def fetch_entry_list_meta(req, year, month):
    if req.method != "GET":
        return HttpResponse(status=405)

    try:
        total_entries = _get_entries_for_month(req.user, year, month).count()
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

        start = (page - 1) * ENTRIES_PER_PAGE
        end = start + ENTRIES_PER_PAGE
        window_entries = list(entries_qs[start:end])

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
        entry = Entry.objects.get(id=entry_id, owner=req.user)

        photos = Photo.objects.filter(entry=entry)
        image_urls = [
            reverse("journal:serve-photo", args=[photo.id]) for photo in photos
        ]

        decrypted_content = decrypt_with_key(
            key=req.user.user_key, encrypted=entry.content
        ).decode("utf-8")

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
            if 11 <= mod100 <= 13:
                return "th"
            mod10 = integer % 10
            if mod10 == 1:
                return "st"
            elif mod10 == 2:
                return "nd"
            elif mod10 == 3:
                return "rd"
            return "th"

        date_display = (
            f"{days[date_obj.weekday() + 1 if date_obj.weekday() < 6 else 0]}, "
            f"{date_obj.day}{get_ordinal_suffix(date_obj.day)}"
        )

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
        entry = Entry.objects.get(id=entry_id, owner=req.user)
        photos = Photo.objects.filter(entry=entry)
        image_urls = [
            reverse("journal:serve-photo", args=[photo.id]) for photo in photos
        ]
        return render(req, "journal/pages/entry-images.html", {"urls": image_urls})
    except Exception as e:
        return HttpResponse(status=404, content=str(e).encode())


@login_required(login_url="/auth/login")
def empty_page(req):
    return render(req, "journal/pages/blank-page.html")


@login_required(login_url="/auth/login")
def account_panel(req):
    if not req.headers.get("X-Requested-With") == "XMLHttpRequest":
        return HttpResponseBadRequest("Panel endpoint only.".encode())
    return render(req, "journal/components/navpanels/account.html", {"user": req.user})


@login_required(login_url="/auth/login")
def journal_panel(req):
    if not req.headers.get("X-Requested-With") == "XMLHttpRequest":
        return HttpResponseBadRequest("Panel endpoint only.".encode())

    settings = JournalSettings.objects.filter(owner=req.user).first()
    return render(
        req,
        "journal/components/navpanels/journal.html",
        {"colour": settings.colour},
    )


@login_required(login_url="/auth/login")
def sticker_panel(req):
    if not req.headers.get("X-Requested-With") == "XMLHttpRequest":
        return HttpResponseBadRequest("Panel endpoint only.".encode())

    try:
        owned_packs = (
            OwnedPack.objects.filter(owner=req.user)
            .select_related("pack")
            .prefetch_related("pack__stickers")
        )
        grouped = [
            {
                "pack": owned.pack,
                "stickers": [
                    {
                        "id": sticker.id,
                        "name": sticker.name,
                        "url": reverse("journal:serve-sticker", args=[sticker.id]),
                    }
                    for sticker in owned.pack.stickers.all()
                ],
            }
            for owned in owned_packs
        ]

    except Exception as e:
        return HttpResponse(status=500, content=str(e).encode())

    return render(req, "journal/components/navpanels/sticker.html", {"packs": grouped})


@login_required(login_url="/auth/login")
def place_sticker(req):
    if req.method != "POST":
        return HttpResponseBadRequest("POST endpoint only".encode())

    try:
        x = round(float(req.POST.get("x", "")), 2)
        y = round(float(req.POST.get("y", "")), 2)
        width = round(float(req.POST.get("width", "")), 2)
        height = round(float(req.POST.get("height", "")), 2)
        id = int(req.POST.get("sticker_id", ""))
        sticker = Sticker.objects.filter(pk=id).first()
        placed = StickerPosition(
            x=x,
            y=y,
            width=width,
            height=height,
            sticker=sticker,
            owner=req.user,
            page=req.POST.get("page_id"),
        )
        placed.save()
    except Exception as e:
        return HttpResponse(status=500, content=str(e).encode())
    else:
        return HttpResponse(status=200, content=str(placed.pk).encode())


@login_required(login_url="/auth/login")
def delete_sticker_placement(req, placement_id):
    if req.method != "DELETE":
        return HttpResponseBadRequest("DELETE endpoint only".encode())

    try:
        placement = StickerPosition.objects.filter(
            pk=placement_id, owner=req.user
        ).first()
        placement.delete()
    except Exception as e:
        return HttpResponse(status=500, content=str(e).encode())

    return HttpResponse(status=200)


@login_required(login_url="/auth/login")
def move_sticker_placement(req, placement_id):
    if req.method != "PUT":
        return HttpResponseBadRequest("PUT endpoint only".encode())

    try:
        placement = StickerPosition.objects.filter(
            pk=placement_id, owner=req.user
        ).first()
        data = json.loads(req.body)

        placement.x = data["x"]
        placement.y = data["y"]
        placement.page = data["page"]

        placement.save()
    except Exception as e:
        return HttpResponse(status=500, content=str(e).encode())

    return HttpResponse(status=200)


@login_required(login_url="/auth/login")
def resize_sticker_placement(req, placement_id):
    if req.method != "PUT":
        return HttpResponseBadRequest("PUT endpoint only".encode())

    try:
        placement = StickerPosition.objects.filter(
            pk=placement_id, owner=req.user
        ).first()
        data = json.loads(req.body)

        placement.width = data["width"]
        placement.height = data["height"]

        placement.save()
    except Exception as e:
        return HttpResponse(status=500, content=str(e).encode())

    return HttpResponse(status=200)


@login_required(login_url="/auth/login")
def sticker_positions_for_page(req, page_id):
    if req.method != "GET":
        return HttpResponseBadRequest("POST endpoint only".encode())

    positions = StickerPosition.objects.filter(
        owner=req.user, page=page_id
    ).select_related("sticker")

    return JsonResponse(
        {
            "stickers": [
                {
                    "id": pos.id,
                    "image_url": req.build_absolute_uri(
                        reverse("journal:serve-sticker", args=[pos.sticker.id])
                    ),
                    "x": float(pos.x),
                    "y": float(pos.y),
                    "width": float(pos.width),
                    "height": float(pos.height),
                }
                for pos in positions
            ]
        }
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
        return HttpResponse(status=500, content=str(e).encode())
    else:
        return HttpResponseRedirect("/")


# ── Onboarding ────────────────────────────────────────────────────────────────

ONBOARDING_STEPS = [0, 1]


@login_required(login_url="/auth/login")
def onboarding(req, step):
    if step not in ONBOARDING_STEPS:
        return HttpResponseRedirect(reverse("journal:home"))

    # Already fully onboarded → go home
    settings = JournalSettings.objects.filter(owner=req.user).first()
    if settings and settings.belongs_to:
        return HttpResponseRedirect(reverse("journal:home"))

    # ── Step 0: pick a colour ─────────────────────────────────────────────────
    if step == 0:
        if req.method == "POST":
            colour = req.POST.get("colour", "6f4518").lstrip("#")

            # Create (or update) the settings row with the chosen colour.
            # belongs_to is intentionally left blank so home_view knows they
            # haven't finished onboarding yet.
            settings, _ = JournalSettings.objects.update_or_create(
                owner=req.user,
                defaults={"colour": colour},
            )
            return HttpResponseRedirect(reverse("journal:onboarding", args=[1]))

        # GET – use existing colour if the user is returning to this step
        colour = settings.colour if settings else "6f4518"
        return render(req, "journal/pages/onboarding/step0.html", {"colour": colour})

    # ── Step 1: enter name ────────────────────────────────────────────────────
    if step == 1:
        # Can't reach step 1 without a settings row (i.e. without doing step 0)
        if settings is None:
            return HttpResponseRedirect(reverse("journal:onboarding", args=[0]))

        if req.method == "POST":
            belongs_to = req.POST.get("belongs_to", "").strip()
            if belongs_to:
                settings.belongs_to = belongs_to
                settings.save()
                return HttpResponseRedirect(reverse("journal:home"))
            # Empty name — re-render with an error
            return render(
                req,
                "journal/pages/onboarding/step1.html",
                {"colour": settings.colour, "error": "Please enter your name."},
            )

        return render(
            req,
            "journal/pages/onboarding/step1.html",
            {"colour": settings.colour},
        )

    return HttpResponseRedirect(reverse("journal:home"))

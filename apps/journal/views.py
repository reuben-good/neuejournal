from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import (
    HttpResponse,
)
from django.shortcuts import render

from apps.helpers.encryption import encrypt_with_key

from .models import Entry, Photo


# Create your views here.
def home_view(req):
    if req.user.is_authenticated:
        return render(req, "journal/journal.html")
    else:
        return render(req, "journal/landing.html")


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

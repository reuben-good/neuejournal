from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import (
    HttpResponse,
)
from django.shortcuts import render

from apps.helpers.encryption import encrypt_with_key

from .models import Entry


# Create your views here.
def home_view(req):
    if req.user.is_authenticated:
        return render(req, "journal/journal.html")
    else:
        return render(req, "journal/landing.html")


@login_required(login_url="/auth/login")
def create_entry(req):
    content = req.POST.get("content", "").strip()
    entry_type = req.POST.get("entry_type", "").strip()

    if len(content) > 0 and len(entry_type) > 0:
        try:
            entry = Entry(
                owner=req.user,
                content=encrypt_with_key(key=req.user.user_key, data=content.encode()),
                type=entry_type,
                date=datetime.today(),
            )
            entry.save()
        except Exception as e:
            return HttpResponse(content=e, status=503)
        else:
            return HttpResponse(status=200)
    else:
        return HttpResponse(content="Must have content".encode(), status=503)

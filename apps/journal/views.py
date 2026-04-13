from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseNotFound
from django.shortcuts import render
from datetime import datetime

from apps.helpers.encryption import decrypt_with_key, encrypt_with_key

from .models import Entry

def fetch_entry(user, date: datetime):
    try:
        entry, created = Entry.objects.get_or_create(
            date=date,
            owner=user,
            pk=(user.id, date)
        )
    except Exception as e:
        raise e
    else:
        return entry, created


# Create your views here.
@login_required(login_url="/auth/login")
def home_view(req):
    today = datetime.today()
    try:
        entry, created = fetch_entry(user=req.user, date=today)
    except Exception as e:
        return HttpResponse(content=e, status=503)
    
    if req.method == "POST":
        try:
            entry.content = encrypt_with_key(key=req.user.user_key, data=req.body)
            entry.save()
            return HttpResponse("Saved entry", status=200)
        except Exception as e:
            return HttpResponse(content=str(e), status=503)
    
    # Handle GET request
    if created:
        return render(req, "journal/journal.html", {"date": today.strftime("%d/%m/%Y")})
    else:
        content = decrypt_with_key(key=req.user.user_key, encrypted=entry.content).decode().strip()
        return render(req, "journal/journal.html", {"date": today.strftime("%d/%m/%Y"), "content": content})


@login_required(login_url="/auth/login")
def entry(req, day, month, year):
    try:
        entry_date = datetime.fromisoformat(f'{year}-{month}-{day}')
    except ValueError:
        return HttpResponseNotFound()

    if req.method == "GET":
        try:
            entry, created = fetch_entry(user=req.user, date=entry_date)
        except Exception as e:
            return HttpResponse(content=e, status=503)
        else:
            if created:
                return render(req, "journal/journal.html", {"date": entry_date.strftime("%d/%m/%Y")})
            else:
                content = decrypt_with_key(key=req.user.user_key, encrypted=entry.content).decode().strip()
                return render(req, "journal/journal.html", {"date": entry_date.strftime("%d/%m/%Y"), "content": content})

    elif req.method == "POST":
        try:
            entry, created = fetch_entry(user=req.user, date=entry_date)
        except Exception as e:
            return HttpResponse(content=e, status=503)
        else:
            if created:
                return Http404()
            else:
                entry.content = encrypt_with_key(key=req.user.user_key, data=req.body)
                entry.save()
                return HttpResponse("Saved entry", status=200)
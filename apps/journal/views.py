import json
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import render
from datetime import datetime

from apps.helpers.encryption import decrypt_with_key, encrypt_with_key

from .models import Entry, Month

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

def fetch_entry_days(user, month: int):
    try:
        dates = Entry.objects.all().filter(owner=user).annotate(month=Month('date')).values_list("date")
    except Exception as e:
        raise e
    else:
        result = {}
        for date in dates:
            day = date[0].day
            month_val = date[0].month
            year_val = date[0].year
            key = (month_val, year_val)
            if key not in result:
                result[key] = {"month": month_val, "year": year_val, "days": []}
            result[key]["days"].append(day)
        return list(result.values())


def handle_entry(req, date: datetime, entry: Entry, created: bool):
    try:
        days = fetch_entry_days(req.user, date.month)
    except Exception as e:
        print(e)
        days = []

    if created:
        entry.content = encrypt_with_key(key=req.user.user_key, data="\n".encode())
        entry.save()
        return render(req, "journal/journal.html", {"date": date.strftime("%d/%m/%Y"), "entries": json.dumps(days)})
    else:
        content = decrypt_with_key(key=req.user.user_key, encrypted=entry.content).decode().strip()
        return render(req, "journal/journal.html", {"date": date.strftime("%d/%m/%Y"), "entries": json.dumps(days), "content": content})

# Create your views here.
@login_required(login_url="/auth/login")
def home_view(req):
    today = datetime.today()
    try:
        entry, created = fetch_entry(user=req.user, date=today)
    except Exception as e:
        return HttpResponse(content=e, status=503)
    else:
        return handle_entry(req, today, entry, created)

@login_required(login_url="/auth/login")
def load_entry(req, day, month, year):
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
            return handle_entry(req, entry_date, entry, created)
    else:
        return HttpResponse(content="Method Not Allowed".encode(), status=405)

@login_required(login_url="/auth/login")
def save_entry(req, day, month, year):
    try:
        entry_date = datetime.fromisoformat(f'{year}-{month}-{day}')
    except ValueError:
        return HttpResponseNotFound()

    try:
        entry, created = fetch_entry(user=req.user, date=entry_date)
    except Exception as e:
        return HttpResponse(content=e, status=503)
    else:
        if created: # if an object has been created from a save route, it shouldn't exist as entries are created on the get request for a date
            entry.delete()
            return Http404()
        else:
            entry.content = encrypt_with_key(key=req.user.user_key, data=req.body)
            entry.save()
            return HttpResponse("Saved entry", status=200)

@login_required(login_url="/auth/login")
def delete_entry(req, day, month, year):
    try:
        entry_date = datetime.fromisoformat(f'{year}-{month}-{day}')
    except ValueError:
        return HttpResponseNotFound()

    try:
        entry, created = fetch_entry(user=req.user, date=entry_date)
    except Exception as e:
        return HttpResponse(content=e, status=503)
    else:
        try:
            prev_entry = entry.get_previous_by_date()
        except Exception:
            prev_entry = None
        entry.delete()
        if prev_entry:
            day = str(prev_entry.date.day).zfill(2)
            month = str(prev_entry.date.month).zfill(2)
            year = prev_entry.date.year
            return HttpResponseRedirect(f"/entry/{day}/{month}/{year}")
        else:
            return HttpResponseRedirect("/")

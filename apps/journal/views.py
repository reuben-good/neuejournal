import json
import re
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import render
from datetime import datetime

from apps.helpers.encryption import decrypt_with_key, encrypt_with_key

from .models import Entry, Mood, Month

def fetch_entry(user, date: datetime):
    """Either fetch or create an entry in the database. Returns the entry object and a boolean to say if it was created or not"""
    try:
        entry, created = Entry.objects.get_or_create(
            date=date,
            owner=user,
        )
    except Exception as e:
        raise e
    else:
        return entry, created

def fetch_entry_days(user):
    """Fetch all the days which have entries and group them by month"""
    try:
        dates = Entry.objects.all().filter(owner=user).annotate(month=Month('date')).values_list("date")
    except Exception as e:
        raise e
    else:
        result = {}
        for date in dates:
            # Convert the values list to a Python list
            day = date[0].day
            month_val = date[0].month
            year_val = date[0].year
            key = (month_val, year_val)
            if key not in result:
                result[key] = {"month": month_val, "year": year_val, "days": []}
            result[key]["days"].append(day)
        return list(result.values())


def handle_entry(req, date: datetime, entry: Entry, created: bool):
    """Handle the rendering of a page based on the result of fetch_entry"""
    try:
        # Fetch the days which this user has entries for to show them in the datepicker
        days = fetch_entry_days(req.user)
    except Exception as e:
        print(e)
        days = []

    if created:
        # Set the content of a new record to just a newline for Quill.js
        entry.content = encrypt_with_key(key=req.user.user_key, data="\n".encode())
        entry.save()
        return render(req, "journal/journal.html", {"date": date.strftime("%d/%m/%Y"), "entries": json.dumps(days)})
    else:
        # Decrypt the record's content before sending it to the client
        content = decrypt_with_key(key=req.user.user_key, encrypted=entry.content).decode().strip()
        return render(req, "journal/journal.html", {"date": date.strftime("%d/%m/%Y"), "entries": json.dumps(days), "content": content})

# Create your views here.
def home_view(req):
    if req.user.is_authenticated:
        today = datetime.today()
        try:
            entry, created = fetch_entry(user=req.user, date=today)
        except Exception as e:
            return HttpResponse(content=e, status=503)
        else:
            return handle_entry(req, today, entry, created)
    else:
        return render(req, "journal/landing.html")

@login_required(login_url="/auth/login")
def load_entry(req, day, month, year):
    try:
        # Ensure the date parameters match a valid date and format it into a datetime object
        entry_date = datetime.fromisoformat(f'{year}-{month}-{day}')
    except ValueError:
        return HttpResponseNotFound()

    if req.method == "GET":
        try:
            # Try to get or create an entry with the requested date
            entry, created = fetch_entry(user=req.user, date=entry_date)
        except Exception as e:
            return HttpResponse(content=e, status=503)
        else:
            return handle_entry(req, entry_date, entry, created)
    else:
        # The client can only make a GET request to this page
        return HttpResponse(content="Method Not Allowed".encode(), status=405)

@login_required(login_url="/auth/login")
def save_entry(req, day, month, year):
    try:
        # Ensure the date parameters match a valid date and format it into a datetime object
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
            # Encrypt the new content and save it into the entry
            entry.content = encrypt_with_key(key=req.user.user_key, data=req.body)
            entry.save()
            return HttpResponse("Saved entry", status=200)

@login_required(login_url="/auth/login")
def delete_entry(req, day, month, year):
    try:
        # Ensure the date parameters match a valid date and format it into a datetime object
        entry_date = datetime.fromisoformat(f'{year}-{month}-{day}')
    except ValueError:
        return HttpResponseNotFound()

    try:
        entry, created = fetch_entry(user=req.user, date=entry_date)
    except Exception as e:
        return HttpResponse(content=e, status=503)
    else:
        try:
            # Try to find an entry before this one's date value
            prev_entry = entry.get_previous_by_date()
        except Exception:
            prev_entry = None
        entry.delete()
        if prev_entry:
            # If a previous entry is found, navigate the user to that entry, otherwise send them to the root
            day = str(prev_entry.date.day).zfill(2)
            month = str(prev_entry.date.month).zfill(2)
            year = prev_entry.date.year
            return HttpResponseRedirect(f"/entry/{day}/{month}/{year}")
        else:
            return HttpResponseRedirect("/")

HAPPINESS_CHOICES = {
    "very-sad": -1.0,
    "sad": -0.5,
    "neutral": 0.0,
    "happy": 0.5,
    "very-happy": 1.0,
}

@login_required(login_url="/auth/login")
def set_mood(req, day, month, year, level):
    if req.method == "POST":
        try:
            # Ensure the date parameters match a valid date and format it into a datetime object
            entry_date = datetime.fromisoformat(f'{year}-{month}-{day}')
            if level not in HAPPINESS_CHOICES.keys():
                raise Exception
        except ValueError:
            return HttpResponseNotFound()

        try:
            entry, created = fetch_entry(user=req.user, date=entry_date)
            mood, updated = Mood.objects.update_or_create(
                owner=req.user,
                entry=entry,
                defaults={'happiness': HAPPINESS_CHOICES[level]}
            )
            mood.save()
        except Exception as e:
            print(e)
            return HttpResponse(status=500)
        else:
            return HttpResponse(status=200)
    else:
        return HttpResponse(content="Method Not Allowed".encode(), status=405)

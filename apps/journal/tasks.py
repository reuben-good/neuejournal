from celery.schedules import crontab
from django.template.loader import render_to_string

from apps.helpers.email import generate_email_image_urls, send_email
from config.celery import app


@app.task
def test(arg):
    print(arg)


@app.task
def monthly_recap():
    from django.utils import timezone

    from apps.helpers.encryption import decrypt_with_key
    from apps.journal.models import Entry, Photo
    from apps.neue_accounts.models import NeueUser

    today = timezone.now().date()
    users = NeueUser.objects.all()

    for user in users:
        if user.is_active:
            entries = Entry.objects.filter(owner=user, date__month=today.month)

            if not entries.exists():
                print("No entries")
                continue

            grouped_entries = {}
            for entry in entries:
                entry_type = entry.type
                if entry_type not in grouped_entries:
                    grouped_entries[entry_type] = []

                photos = Photo.objects.filter(entry=entry)
                # Generate token-protected URLs for images
                image_urls = generate_email_image_urls(
                    photos, expires_in_hours=24, protocol="http"
                )

                grouped_entries[entry_type].append(
                    {
                        "date": entry.date,
                        "content": decrypt_with_key(
                            key=user.user_key, encrypted=entry.content
                        ).decode("utf-8"),
                        "images": image_urls,
                    }
                )

            # Render email template with token-protected image URLs
            html_content = render_to_string(
                "journal/emails/monthly-recap.html",
                {
                    "event": grouped_entries.get("event", []),
                    "lesson": grouped_entries.get("lesson", []),
                    "milestone": grouped_entries.get("milestone", []),
                    "BASE_URL": "127.0.0.1:8000",
                },
            )

            # Send email
            send_email(
                subject="Your monthly recap",
                text_content="Your monthly recap",
                html_content=html_content,
                address=user.email,
            )
            print(f"Monthly recap email sent to {user.email}")


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Use .s() to create a task signature (deferred execution)

    # Example
    # sender.add_periodic_task(10.0, users.s(), name="every 10")

    sender.add_periodic_task(
        crontab(hour=1, minute=0, day_of_month=1),
        monthly_recap.s("Happy first day of month!"),
    )

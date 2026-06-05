import six
from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import EmailMultiAlternatives


def send_email(subject: str, address: str, text_content: str, html_content: str):
    try:
        msg = EmailMultiAlternatives(
            subject,
            text_content,
            settings.EMAIL_HOST_USER,
            [address],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
    except Exception as e:
        print(f"Error sending email: {e}")


class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            six.text_type(user.pk)
            + six.text_type(timestamp)
            + six.text_type(user.is_active)
        )


def generate_email_image_urls(
    photos, domain=None, expires_in_hours=24, protocol="https"
):
    """Generate token-protected URLs for photos in emails.

    Args:
        photos: List of Photo model instances
        domain: Domain name (defaults to first ALLOWED_HOST or EMAIL_DOMAIN setting)
        expires_in_hours: How long tokens are valid (default: 24 hours)
        protocol: Protocol to use (default: https)

    Returns:
        List of token-protected URLs that can be embedded in emails
    """
    if domain is None:
        # Try to use EMAIL_DOMAIN setting first, then ALLOWED_HOSTS
        domain = getattr(settings, "EMAIL_DOMAIN", None)
        if not domain and settings.ALLOWED_HOSTS:
            domain = settings.ALLOWED_HOSTS[0]
        if not domain:
            domain = "localhost:8000"

    urls = []
    for photo in photos:
        # Generate token for this photo
        token = photo.generate_email_token(expires_in_hours=expires_in_hours)
        # Build the URL
        url = f"{protocol}://{domain}/photo/{photo.id}/{token}"
        urls.append(url)

    return urls

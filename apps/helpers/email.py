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

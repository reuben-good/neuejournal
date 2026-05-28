import secrets
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django_rls.models import RLSModel
from django_rls.policies import UserPolicy

from apps.helpers.storages import sticker_storage
from apps.neue_accounts.models import NeueUser


# Create your models here.
class Entry(RLSModel):
    class Type(models.TextChoices):
        MILESTONE = "milestone", "Milestone"
        LESSON = "lesson", "Lesson"
        EVENT = "event", "Event"

    owner = models.ForeignKey(NeueUser, on_delete=models.CASCADE)
    date = models.DateField()
    content = models.BinaryField()
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.MILESTONE,
    )

    class Meta:
        rls_policies = [UserPolicy("owner_policy", user_field="owner")]


class Photo(RLSModel):
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="photos/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    email_token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    email_token_expires = models.DateTimeField(null=True, blank=True)

    def clean(self):
        if self.pk is None:
            count = Photo.objects.filter(entry=self.entry).count()
            if count >= 3:
                raise ValidationError("An entry can have at most 3 images.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def generate_email_token(self, expires_in_hours=24):
        """Generate a time-limited token for email access.

        Args:
            expires_in_hours: Number of hours the token is valid (default: 24)

        Returns:
            The generated token string
        """
        self.email_token = secrets.token_urlsafe(48)
        self.email_token_expires = timezone.now() + timedelta(hours=expires_in_hours)
        self.save()
        return self.email_token

    class Meta:
        rls_policies = [UserPolicy("owner_policy", user_field="entry__owner")]


class JournalSettings(RLSModel):
    owner = models.ForeignKey(NeueUser, on_delete=models.CASCADE)
    colour = models.CharField(max_length=6, default="6f4518")
    belongs_to = models.CharField(max_length=70)

    class Meta:
        rls_policies = [UserPolicy("owner_policy", user_field="owner")]


class StickerPack(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    artist = models.CharField(max_length=100)


class OwnedPack(RLSModel):
    owner = models.ForeignKey(NeueUser, on_delete=models.CASCADE)
    pack = models.ForeignKey(StickerPack, on_delete=models.CASCADE)
    purchase_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        rls_policies = [UserPolicy("owner_policy", user_field="owner")]


class Sticker(models.Model):
    pack = models.ForeignKey(
        StickerPack, on_delete=models.CASCADE, related_name="stickers"
    )
    name = models.CharField(max_length=100)
    image = models.ImageField(
        storage=sticker_storage,
        upload_to="",
    )

    def __str__(self) -> str:
        return str(self.name)


class StickerPosition(RLSModel):
    owner = models.ForeignKey(NeueUser, on_delete=models.CASCADE)
    sticker = models.ForeignKey(Sticker, on_delete=models.CASCADE)
    page = models.CharField(max_length=200)
    width = models.DecimalField(max_digits=10, decimal_places=2)
    height = models.DecimalField(max_digits=10, decimal_places=2)
    x = models.DecimalField(max_digits=5, decimal_places=2)
    y = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        rls_policies = [UserPolicy("owner_policy", user_field="owner")]

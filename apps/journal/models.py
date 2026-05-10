from django.core.exceptions import ValidationError
from django.db import models
from django_rls.models import RLSModel
from django_rls.policies import UserPolicy

from ..neue_accounts.models import NeueUser


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

    def clean(self):
        if self.pk is None:
            count = Photo.objects.filter(entry=self.entry).count()
            if count >= 3:
                raise ValidationError("An entry can have at most 3 images.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        rls_policies = [UserPolicy("owner_policy", user_field="entry__owner")]


class JournalSettings(RLSModel):
    owner = models.ForeignKey(NeueUser, on_delete=models.CASCADE)
    colour = models.CharField(max_length=6, default="8ecae6")

    class Meta:
        rls_policies = [UserPolicy("owner_policy", user_field="owner")]

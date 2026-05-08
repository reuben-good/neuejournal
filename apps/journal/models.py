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


class Mood(RLSModel):
    HAPPINESS_CHOICES = [
        ("very-sad", -1.0),
        ("sad", -0.5),
        ("neutral", 0.0),
        ("happy", 0.5),
        ("very-happy", 1.0),
    ]

    owner = models.ForeignKey(NeueUser, on_delete=models.CASCADE)
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE)
    happiness = models.DecimalField(
        max_digits=2, decimal_places=1, choices=HAPPINESS_CHOICES
    )

    class Meta:
        rls_policies = [UserPolicy("owner_policy", user_field="owner")]
        ordering = ["-entry__date"]


class Month(models.Func):
    function = "EXTRACT"
    template = "%(function)s(MONTH from %(expressions)s)"
    output_field = models.IntegerField()

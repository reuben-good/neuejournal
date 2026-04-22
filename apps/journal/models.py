from xml.parsers.expat import model
from django.db import models
from django_rls.models import RLSModel
from django_rls.policies import UserPolicy

from ..neue_accounts.models import NeueUser

# Create your models here.
class Entry(RLSModel):
    owner = models.ForeignKey(NeueUser, on_delete=models.CASCADE)
    date = models.DateField()
    content = models.BinaryField()

    class Meta:
        rls_policies = [
            UserPolicy('owner_policy', user_field='owner')
        ]

        unique_together = ('owner', 'date')

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
    happiness = models.DecimalField(max_digits=2, decimal_places=1, choices=HAPPINESS_CHOICES)

    class Meta:
        rls_policies = [
            UserPolicy('owner_policy', user_field='owner')
        ]

        unique_together = ('owner', 'entry')

class Month(models.Func):
    function = 'EXTRACT'
    template = '%(function)s(MONTH from %(expressions)s)'
    output_field = models.IntegerField()

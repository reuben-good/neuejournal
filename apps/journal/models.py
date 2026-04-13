from django.db import models
from django_rls.models import RLSModel
from django_rls.policies import UserPolicy

from ..neue_accounts.models import NeueUser

# Create your models here.
class Entry(RLSModel):
    owner = models.ForeignKey(NeueUser, on_delete=models.CASCADE)
    date = models.DateField()
    pk = models.CompositePrimaryKey("owner", "date")
    content = models.BinaryField()

    class Meta:
        rls_policies = [
            UserPolicy('owner_policy', user_field='owner')
        ]

        unique_together = ('owner', 'date')

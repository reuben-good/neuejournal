from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from apps.helpers.encryption import generate_key


# Create your models here.
class NeueUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email, password, **extra_fields)

    def get_by_natural_key(self, username):
        email = self.normalize_email(username)
        return self.get(**{self.model.USERNAME_FIELD: email})


class NeueUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)
    user_key = models.BinaryField()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = NeueUserManager()

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if not self.user_key:
            self.user_key = generate_key()

        super().save(*args, **kwargs)

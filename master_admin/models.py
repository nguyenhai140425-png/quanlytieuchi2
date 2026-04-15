import datetime
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


class UserRole(models.IntegerChoices):
    USER = 1
    ADMIN = 2

class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, username, email, password, **extra_fields):
        if not username:
            raise ValueError("The given username must be set")
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_active", True)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", UserRole.ADMIN)
        assert (
            extra_fields.get("role") == UserRole.ADMIN
        ), f"Superuser must have type={UserRole.ADMIN}."
        return self._create_user(username, email, password, **extra_fields)

class User(AbstractBaseUser):
    username = models.CharField(max_length=150, unique=True)
    name = models.CharField(max_length=128, default="")
    password = models.CharField(max_length=128)
    email = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    last_login = models.DateTimeField(blank=True, null=True)
    role = models.PositiveSmallIntegerField(
        choices=UserRole.choices, default=UserRole.ADMIN
    )
    objects = UserManager()
    EMAIL_FIELD = "email"
    USERNAME_FIELD = "username"

class Category(models.Model):
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=15, decimal_places=0)
    fromDate = models.DateField()
    toDate = models.DateField()
    year = models.IntegerField(default=datetime.date.today().year)
    def __str__(self):
        return self.name

class Event(models.Model):
    title = models.CharField(max_length=200)
    totalUserAllocated = models.IntegerField(default=0)
    totalAmount = models.DecimalField(max_digits=15, decimal_places=0)
    fromDate = models.DateField()
    toDate = models.DateField()
    year = models.IntegerField(default=datetime.date.today().year)
    is_adhoc = models.BooleanField(default=False)
    is_reviewed = models.BooleanField(default=True)
    categories = models.ManyToManyField(Category)
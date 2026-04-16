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
    email = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    role = models.PositiveSmallIntegerField(
        choices=UserRole.choices, default=UserRole.ADMIN
    )
    objects = UserManager()
    EMAIL_FIELD = "email"
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ['email']

    @property
    def is_staff(self):
        return self.role == UserRole.ADMIN

    @property
    def is_superuser(self):
        return self.role == UserRole.ADMIN

    def has_perm(self, perm, obj=None):
        return self.role == UserRole.ADMIN

    def has_module_perms(self, app_label):
        return self.role == UserRole.ADMIN

#class Category(models.Model):
#    name = models.CharField(max_length=100)
#    amount = models.DecimalField(max_digits=15, decimal_places=0)
#    fromDate = models.DateField()
#    toDate = models.DateField()
#    year = models.IntegerField(default=datetime.date.today().year)
#    def __str__(self):
#        return self.name
class Category(models.Model):
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    fromDate = models.DateField(null=True, blank=True)
    toDate = models.DateField(null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)

    is_fixed = models.BooleanField(default=False)  # 🔥 THÊM DÒNG NÀY
class EventApprovalStatus(models.IntegerChoices):
    PENDING = 1, 'Chờ duyệt'
    APPROVED = 2, 'Đã duyệt'
    REJECTED = 3, 'Không duyệt'

class Event(models.Model):
    title = models.CharField(max_length=200)
    totalUserAllocated = models.IntegerField(default=0)
    totalAmount = models.DecimalField(max_digits=15, decimal_places=0)
    fromDate = models.DateField()
    toDate = models.DateField()
    year = models.IntegerField(default=datetime.date.today().year)
    is_adhoc = models.BooleanField(default=False)
    approval_status = models.PositiveSmallIntegerField(
        choices=EventApprovalStatus.choices, default=EventApprovalStatus.APPROVED
    )
#    categories = models.ManyToManyField(Category)
    categories = models.ManyToManyField(
    Category,
    through='EventCategory'
)
class EventCategory(models.Model):
    event = models.ForeignKey('Event', on_delete=models.CASCADE)
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

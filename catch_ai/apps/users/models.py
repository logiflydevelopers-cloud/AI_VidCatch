from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from nanoid import generate


def generate_user_id():
    return f"usr_{generate(size=10)}"


class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):

        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            **extra_fields
        )

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)

        return user


    def create_superuser(self, email, password=None, **extra_fields):

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("login_provider", "email")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):

    LOGIN_CHOICES = (
        ("email", "Email"),
        ("google", "Google"),
    )

    id = models.CharField(
        primary_key=True,
        max_length=20,
        default=generate_user_id,
        editable=False
    )

    username = models.CharField(max_length=150)

    email = models.EmailField(
        unique=True,
        db_index=True
    )

    # how user registered
    login_provider = models.CharField(
        max_length=20,
        choices=LOGIN_CHOICES,
        default="email"
    )

    # store google account id
    google_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)

    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email
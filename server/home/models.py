from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Roles(models.TextChoices):
        STAFF = "STAFF", "Staff"
        APPROVER_L1 = "APPROVER_L1", "Approver Level 1"
        APPROVER_L2 = "APPROVER_L2", "Approver Level 2"
        FINANCE = "FINANCE", "Finance"

    role = models.CharField(
        max_length=32,
        choices=Roles.choices,
        default=Roles.STAFF,
        help_text="Determines which workflow permissions the user has.",
    )

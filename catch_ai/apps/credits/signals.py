from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import UserCredits

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_credits(sender, instance, created, **kwargs):
    if created:
        UserCredits.objects.create(
            user=instance,
            total_credits=1000  # default free credits
        )
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from apps.credits.services import add_credits

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_credits(sender, instance, created, **kwargs):
    if created:
        add_credits(instance, 50, "Signup bonus")
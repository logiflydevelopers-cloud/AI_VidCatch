from django.core.management.base import BaseCommand
from apps.features.models import Features


class Command(BaseCommand):
    help = "Create default features"

    def handle(self, *args, **kwargs):

        features = [
            {
                "name": "Text to Video",
                "feature_type": "text_to_video",
            },
            {
                "name": "Image to Video",
                "feature_type": "image_to_video",
            },
            {
                "name": "Background Change",
                "feature_type": "background_change",
            },
            {
                "name": "Background Remove",
                "feature_type": "background_remove",
            },
            {
                "name": "Colorize",
                "feature_type": "colorize",
            },
            {
                "name": "Upscale",
                "feature_type": "upscale",
            },
        ]

        for f in features:
            obj, created = Features.objects.get_or_create(
                feature_type=f["feature_type"],
                defaults=f
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created: {obj.name}"))
            else:
                self.stdout.write(f"Already exists: {obj.name}")
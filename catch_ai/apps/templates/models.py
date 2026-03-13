import uuid
from django.db import models


class Template(models.Model):

    FEATURE_CHOICES = [
        ("text_to_video", "Text to Video"),
        ("image_to_video", "Image to Video"),
        ("background_remove", "Background Remove"),
        ("background_change", "Background Change"),
        ("image_upscale", "Image Upscale"),
        ("image_colorize", "Image Colorize"),
    ]

    id = models.CharField(
        primary_key=True,
        max_length=20,
        editable=False
    )

    name = models.CharField(max_length=255)

    cover_image = models.URLField()

    credit_cost = models.IntegerField()

    feature_type = models.CharField(
        max_length=50,
        choices=FEATURE_CHOICES
    )

    prompt_template = models.TextField(
        blank=True,
        null=True
    )

    input_schema = models.JSONField()

    default_settings = models.JSONField(
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):

        if not self.id:
            self.id = f"tpl_{uuid.uuid4().hex[:8].upper()}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
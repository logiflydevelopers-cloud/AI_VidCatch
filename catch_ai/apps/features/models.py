from django.db import models
from django.core.exceptions import ValidationError
from apps.templates.models import AIModel
import uuid


FEATURE_CHOICES = [
    ("text_to_video", "Text to Video"),
    ("image_to_video", "Image to Video"),
    ("couple_wallpaper", "Couple Wallpaper"),
    ("background_remove", "Background Remove"),
    ("background_change", "Background Change"),
    ("image_upscale", "Image Upscale"),
    ("image_colorize", "Image Colorize")
]

# Create your models here.
class Features(models.Model):

    id = models.CharField(primary_key=True, max_length=20, editable=False)

    name = models.CharField(max_length=255)

    credit_cost = models.IntegerField()

    feature_type = models.CharField(
        max_length=50,
        choices=FEATURE_CHOICES
    )

    allowed_models = models.ManyToManyField(
        AIModel,
        related_name="templates"
    )

    default_model = models.ForeignKey(
        AIModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_templates"
    )

    input_schema = models.JSONField()

    default_settings = models.JSONField(blank=True, null=True)

    display_order = models.IntegerField(default=0)

    is_premium = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # ensure default_model is inside allowed_models
        if self.default_model and self.pk:
            if self.default_model not in self.allowed_models.all():
                raise ValidationError("Default model must be in allowed_models")

        # ensure feature consistency
        if self.default_model:
            if self.default_model.feature_type != self.feature_type:
                raise ValidationError("Model feature_type must match template feature_type")

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"tpl_{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
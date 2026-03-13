import uuid
from django.db import models


FEATURE_CHOICES = [
    ("text_to_video", "Text to Video"),
    ("image_to_video", "Image to Video"),
    ("background_remove", "Background Remove"),
    ("background_change", "Background Change"),
    ("image_upscale", "Image Upscale"),
    ("image_colorize", "Image Colorize"),
]


class AIModel(models.Model):

    id = models.CharField(primary_key=True, max_length=30, editable=False)

    # key used in FastAPI registry
    model_key = models.CharField(max_length=100, unique=True)

    name = models.CharField(max_length=100)

    feature_type = models.CharField(
        max_length=50,
        choices=FEATURE_CHOICES
    )

    provider = models.CharField(max_length=50, blank=True, null=True)

    # cost per generation (credits)
    credit_cost = models.IntegerField(default=1)

    # default model for feature
    is_default = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"mdl_{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.feature_type})"


class Template(models.Model):

    id = models.CharField(primary_key=True, max_length=20, editable=False)

    name = models.CharField(max_length=255)

    cover_image = models.URLField()

    credit_cost = models.IntegerField()

    feature_type = models.CharField(
        max_length=50,
        choices=FEATURE_CHOICES
    )

    # models admin can assign
    allowed_models = models.ManyToManyField(
        AIModel,
        related_name="templates"
    )

    # used for prompt-based models
    prompt_template = models.TextField(blank=True, null=True)

    # dynamic UI schema
    input_schema = models.JSONField()

    # model default parameters
    default_settings = models.JSONField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"tpl_{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
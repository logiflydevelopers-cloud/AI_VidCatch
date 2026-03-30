import uuid
from django.db import models
from django.core.exceptions import ValidationError


FEATURE_CHOICES = [
    ("text_to_video", "Text to Video"),
    ("image_to_video", "Image to Video"),
    ("image_edit", "Image Edit"),
    ("couple_wallpaper", "Couple Wallpaper"),
    ("background_remove", "Background Remove"),
    ("background_change", "Background Change"),
    ("image_upscale", "Image Upscale"),
    ("image_colorize", "Image Colorize")
]

CATEGORY_CHOICES = [
    ("all", "All"),
    ("popular", "Popular"),
    ("family", "Family"),
    ("trending", "Trending"),
    ("love", "Love"),
    ("birthday", "Birthday"),
    ("photoshoot", "Photoshoot"),
    ("new", "New"),
    ("kids", "Kids"),
    ("wedding", "Wedding"),
    ("dance", "Dance"),
    ("bw", "B&W"),
]

import uuid
from django.db import models


class AIModel(models.Model):

    id = models.CharField(primary_key=True, max_length=30, editable=False)

    # key from FastAPI registry
    model_name = models.CharField(max_length=100, unique=True)

    name = models.CharField(max_length=100)

    feature_type = models.CharField(max_length=50)

    feature = models.ForeignKey(
        "features.Features",
        on_delete=models.CASCADE,
        related_name="models",
        null=True,
        blank=True
    )

    provider = models.CharField(max_length=50, blank=True, null=True)

    # 💰 Cost per usage
    credit_cost = models.PositiveIntegerField(default=1)

    # 🔥 NEW: Usage tracking
    total_usage_count = models.PositiveIntegerField(default=0)

    # 🔥 NEW: Total credits consumed (analytics)
    total_credits_used = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    # ============================
    # META (performance + safety)
    # ============================
    class Meta:
        indexes = [
            models.Index(fields=["feature_type"]),
            models.Index(fields=["model_name"]),
            models.Index(fields=["is_active"]),
        ]

    # ============================
    # SAVE
    # ============================
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"mdl_{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    # ============================
    # USAGE TRACKING METHOD 🔥
    # ============================
    def track_usage(self):
        """
        Call this whenever model is used
        """
        self.total_usage_count += 1
        self.total_credits_used += self.credit_cost
        self.save(update_fields=["total_usage_count", "total_credits_used"])

    def __str__(self):
        return f"{self.name} ({self.feature_type})"



class Template(models.Model):

    id = models.CharField(primary_key=True, max_length=20, editable=False)

    name = models.CharField(max_length=255)

    cover_image = models.URLField(max_length=1000, blank=True, null=True)

    preview_media = models.JSONField(default=list, blank=True)

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default="new"
    )

    credit_cost = models.PositiveIntegerField(default=0)

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

    prompt_template = models.TextField(blank=True, null=True)

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
    

class GenerationConfig(models.Model):

    CONFIG_TYPE_CHOICES = (
        ("auto_video", "Auto Video"),
    )

    id = models.CharField(primary_key=True, max_length=20, editable=False)

    name = models.CharField(max_length=255)

    config_type = models.CharField(max_length=50, choices=CONFIG_TYPE_CHOICES)

    # 🔥 CORE LOGIC
    feature_type = models.CharField(max_length=50, choices=FEATURE_CHOICES)

    model = models.ForeignKey(
        AIModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    prompt_template = models.TextField()

    default_settings = models.JSONField(blank=True, null=True)

    # 🔥 CONTROL
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"cfg_{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
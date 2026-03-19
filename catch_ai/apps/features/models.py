from django.db import models
from django.core.exceptions import ValidationError
from apps.templates.models import AIModel
import uuid


class Features(models.Model):

    id = models.CharField(primary_key=True, max_length=20, editable=False)

    name = models.CharField(max_length=255)

    credit_cost = models.PositiveIntegerField(default=0)

    # 🔥 NO CHOICES (dynamic + must match FastAPI registry)
    feature_type = models.CharField(
        max_length=50,
        unique=True
    )

    # ============================
    # MODELS CONFIG
    # ============================
    allowed_models = models.ManyToManyField(
        AIModel,
        related_name="features",
        blank=True
    )

    default_model = models.ForeignKey(
        AIModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_features"
    )

    # ============================
    # CONFIGURATION
    # ============================
    input_schema = models.JSONField(blank=True, null=True)

    default_settings = models.JSONField(blank=True, null=True)

    # ============================
    # UI / CONTROL
    # ============================
    display_order = models.IntegerField(default=0)

    is_premium = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    # ============================
    # VALIDATION
    # ============================
    def clean(self):

        # ----------------------------
        # 1. allowed_models validation
        # ----------------------------
        if self.allowed_models.exists():
            for model in self.allowed_models.all():
                if model.feature_type != self.feature_type:
                    raise ValidationError(
                        f"{model.name} does not belong to {self.feature_type}"
                    )

        # ----------------------------
        # 2. default_model validation
        # ----------------------------
        if self.default_model:

            if self.default_model.feature_type != self.feature_type:
                raise ValidationError(
                    "Default model feature_type mismatch"
                )

            if self.pk and self.default_model not in self.allowed_models.all():
                raise ValidationError(
                    "Default model must be in allowed_models"
                )

        # ----------------------------
        # 3. optional: enforce 1–4 models
        # ----------------------------
        if self.pk:
            model_count = self.allowed_models.count()

            if model_count == 0:
                raise ValidationError("At least 1 model is required")

            if model_count > 4:
                raise ValidationError("Maximum 4 models allowed per feature")

    # ============================
    # SAVE
    # ============================
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"feat_{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
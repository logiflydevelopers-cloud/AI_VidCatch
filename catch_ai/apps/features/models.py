from django.db import models
from django.core.exceptions import ValidationError
from apps.templates.models import AIModel
import uuid

class Features(models.Model):

    id = models.CharField(primary_key=True, max_length=20, editable=False)

    name = models.CharField(max_length=255)

    credit_cost = models.PositiveIntegerField(default=0)

    feature_type = models.CharField(
        max_length=50,
        unique=True
    )

    # ============================
    # MODELS CONFIG
    # ============================
    allowed_models = models.ManyToManyField(
        "templates.AIModel",
        related_name="features",
        blank=True
    )

    default_model = models.ForeignKey(
        "templates.AIModel",
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

    model_mapping = models.JSONField(blank=True, null=True)

    # ============================
    # UI / CONTROL
    # ============================
    display_order = models.IntegerField(default=0)

    is_premium = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    # ============================
    # VALIDATION (ONLY FK SAFE)
    # ============================
    def clean(self):
        super().clean()
        
    # ============================
    # SAVE
    # ============================
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"feat_{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
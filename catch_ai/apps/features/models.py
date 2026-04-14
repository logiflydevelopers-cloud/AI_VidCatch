from django.db import models
import uuid


class Features(models.Model):

    id = models.CharField(primary_key=True, max_length=20, editable=False)

    name = models.CharField(max_length=255)

    feature_type = models.CharField(
        max_length=50,
        unique=True
    )

    is_multi_mode = models.BooleanField(default=False)
    # ✔ True → fast/standard/advanced
    # ✔ False → normal feature

    # ============================
    # CREDITS PER MODE
    # ============================
    credit_cost = models.PositiveIntegerField(default=0)

    credits_config = models.JSONField(blank=True, null=True)

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
    # INPUT SCHEMA
    # ============================
    input_schema = models.JSONField(blank=True, null=True)

    # ============================
    # MODEL MAPPING (fast → modelA)
    # ============================
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
    # SAVE
    # ============================
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f"feat_{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ==========================================================
# FEATURE SETTINGS
# ==========================================================
class FeatureSetting(models.Model):

    # -----------------------------
    # INPUT TYPE (NEW)
    # -----------------------------
    INPUT_TYPE_CHOICES = (
        ("one_image", "One Image"),
        ("two_image", "Two Image"),
    )

    # -----------------------------
    # MODE (EXISTING)
    # -----------------------------
    MODE_CHOICES = (
        ("fast", "Fast"),
        ("standard", "Standard"),
        ("advanced", "Advanced"),
    )

    feature = models.ForeignKey(
        Features,
        on_delete=models.CASCADE,
        related_name="settings"
    )

    input_type = models.CharField(
        max_length=20,
        choices=INPUT_TYPE_CHOICES,
        null=True,
        blank=True
    )

    # fast / standard / advanced
    mode = models.CharField(
        max_length=20,
        choices=MODE_CHOICES
    )

    # duration, aspect_ratio, resolution, generate_audio
    key = models.CharField(max_length=100)

    # select / boolean / slider / number
    type = models.CharField(max_length=50, default="select")

    # [5,10], ["9:16"], [true,false]
    options = models.JSONField(default=list)

    default_value = models.JSONField(null=True, blank=True)

    is_required = models.BooleanField(default=True)

    display_order = models.IntegerField(default=0)

    class Meta:
        unique_together = ("feature", "input_type", "mode", "key")

        ordering = ("input_type", "mode", "display_order")

    def __str__(self):
        return f"{self.feature.name} - {self.input_type or 'default'} - {self.mode} - {self.key}"
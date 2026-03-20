from django.contrib import admin, messages
from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from django.db.models import F

from .models import Template, AIModel
from apps.features.models import Features, FeatureSetting
from apps.services.firebase_storage import upload_file

from apps.credits.models import UserCredits, CreditTransaction

# optional delete
try:
    from apps.services.firebase_storage import delete_file
except:
    delete_file = None

# JSON Editor (install: pip install django-json-widget)
from django_json_widget.widgets import JSONEditorWidget


# ==========================================================
# TEMPLATE ADMIN FORM
# ==========================================================
class TemplateAdminForm(forms.ModelForm):

    cover_image_file = forms.FileField(required=False)
    preview_files = forms.FileField(required=False)

    class Meta:
        model = Template
        fields = "__all__"
        widgets = {
            "input_schema": JSONEditorWidget,
            "default_settings": JSONEditorWidget,
        }

    def clean(self):
        cleaned_data = super().clean()

        default_model = cleaned_data.get("default_model")
        allowed_models = cleaned_data.get("allowed_models")
        feature_type = cleaned_data.get("feature_type")

        if default_model:
            if allowed_models and default_model not in allowed_models:
                raise ValidationError("Default model must be in allowed_models")

            if default_model.feature_type != feature_type:
                raise ValidationError("Model feature_type must match template feature_type")

        return cleaned_data


# ==========================================================
# AI MODEL ADMIN
# ==========================================================
@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "feature_type",
        "provider",
        "credit_cost",
        "is_active",
    )

    list_filter = ("feature_type", "is_active")

    search_fields = ("name", "model_name")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ==========================================================
# TEMPLATE ADMIN
# ==========================================================
@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):

    form = TemplateAdminForm

    list_display = (
        "id", "name", "preview_thumbnail",
        "category", "feature_type", "credit_cost",
        "is_active", "created_at"
    )

    list_filter = ("category", "feature_type", "is_active")
    search_fields = ("name",)

    filter_horizontal = ("allowed_models",)

    readonly_fields = ("id", "created_at", "updated_at")

    # -----------------------------
    # FORM CUSTOMIZATION
    # -----------------------------
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        if "preview_files" in form.base_fields:
            form.base_fields["preview_files"].widget.attrs["multiple"] = True

        return form

    # -----------------------------
    # FILTER MODELS
    # -----------------------------
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "default_model":
            kwargs["queryset"] = AIModel.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "allowed_models":
            kwargs["queryset"] = AIModel.objects.filter(is_active=True)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    # -----------------------------
    # THUMBNAIL
    # -----------------------------
    def preview_thumbnail(self, obj):
        if obj.cover_image:
            return format_html(
                '<img src="{}" style="height:50px;border-radius:6px;" />',
                obj.cover_image
            )
        return "-"

    # -----------------------------
    # SAVE LOGIC
    # -----------------------------
    def save_model(self, request, obj, form, change):

        super().save_model(request, obj, form, change)

        # -----------------------------
        # COVER IMAGE
        # -----------------------------
        cover_file = form.cleaned_data.get("cover_image_file")

        if cover_file:

            if obj.cover_image and delete_file:
                try:
                    delete_file(obj.cover_image)
                except:
                    pass

            path = f"templates/{obj.id}/cover"
            obj.cover_image = upload_file(cover_file, path)

        # -----------------------------
        # PREVIEW FILES
        # -----------------------------
        preview_files = request.FILES.getlist("preview_files")

        if preview_files:

            urls = list(obj.preview_media or [])
            MAX_FILES = 10

            for file in preview_files:

                if len(urls) >= MAX_FILES:
                    break

                if not file.content_type.startswith(("image/", "video/")):
                    raise ValidationError("Only image/video files allowed")

                path = f"templates/{obj.id}/previews"
                url = upload_file(file, path)

                urls.append(url)

            obj.preview_media = urls

        obj.save()

# ==========================================================
# FEATURE ADMIN FORM
# ==========================================================
class FeatureAdminForm(forms.ModelForm):

    fast_model = forms.ModelChoiceField(
        queryset=AIModel.objects.none(),
        required=False,
        label="Fast Model"
    )
    standard_model = forms.ModelChoiceField(
        queryset=AIModel.objects.none(),
        required=False,
        label="Standard Model"
    )
    advanced_model = forms.ModelChoiceField(
        queryset=AIModel.objects.none(),
        required=False,
        label="Advanced Model"
    )

    class Meta:
        model = Features
        fields = "__all__"
        widgets = {
            "input_schema": JSONEditorWidget,
            "credits_config": JSONEditorWidget,
            
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # -----------------------------
        # Allowed models queryset
        # -----------------------------
        if self.data.get("allowed_models"):
            qs = AIModel.objects.filter(
                id__in=self.data.getlist("allowed_models")
            )
        elif self.instance and self.instance.pk:
            qs = self.instance.allowed_models.all()
        else:
            qs = AIModel.objects.filter(is_active=True)

        self.fields["fast_model"].queryset = qs
        self.fields["standard_model"].queryset = qs
        self.fields["advanced_model"].queryset = qs

        # -----------------------------
        # Load existing mapping
        # -----------------------------
        mapping = getattr(self.instance, "model_mapping", None)

        if mapping:
            try:
                self.fields["fast_model"].initial = qs.filter(id=mapping.get("fast")).first()
                self.fields["standard_model"].initial = qs.filter(id=mapping.get("standard")).first()
                self.fields["advanced_model"].initial = qs.filter(id=mapping.get("advanced")).first()
            except Exception:
                pass

        # -----------------------------
        # Multi-mode detection (POST SAFE)
        # -----------------------------
        is_multi_mode = (
            self.data.get("is_multi_mode") in ["on", "true", True]
            or (self.instance and self.instance.is_multi_mode)
        )

        if not is_multi_mode:
            self.fields.pop("fast_model", None)
            self.fields.pop("standard_model", None)
            self.fields.pop("advanced_model", None)

    def clean(self):
        cleaned_data = super().clean()

        allowed_models = cleaned_data.get("allowed_models") or []
        default_model = cleaned_data.get("default_model")

        # -----------------------------
        # Basic validation
        # -----------------------------
        if not allowed_models:
            self.add_error("allowed_models", "At least 1 model is required")
            return cleaned_data

        if len(allowed_models) > 4:
            self.add_error("allowed_models", "Maximum 4 models allowed")

        # -----------------------------
        # Default model validation
        # -----------------------------
        if default_model and default_model not in allowed_models:
            self.add_error(
                "default_model",
                "Default model must be one of the allowed models"
            )

        if not default_model and allowed_models:
            cleaned_data["default_model"] = allowed_models[0]

        # -----------------------------
        # MULTI MODE
        # -----------------------------
        if cleaned_data.get("is_multi_mode"):

            fast = cleaned_data.get("fast_model")
            standard = cleaned_data.get("standard_model")
            advanced = cleaned_data.get("advanced_model")

            if not fast:
                self.add_error("fast_model", "Fast model is required")

            if not standard:
                self.add_error("standard_model", "Standard model is required")

            if not advanced:
                self.add_error("advanced_model", "Advanced model is required")

            if not all([fast, standard, advanced]):
                return cleaned_data

            # Ensure models belong to allowed_models
            for field_name, model in {
                "fast_model": fast,
                "standard_model": standard,
                "advanced_model": advanced,
            }.items():
                if model not in allowed_models:
                    self.add_error(
                        field_name,
                        "Selected model must be in allowed_models"
                    )

            # ==============================
            # CREDITS CONFIG VALIDATION 
            # ==============================
            credits_config = cleaned_data.get("credits_config")

            if credits_config:

                if not isinstance(credits_config, dict):
                    self.add_error("credits_config", "Must be a valid JSON object")
                    return cleaned_data

                # --------------------------
                # Validate base credits
                # --------------------------
                for key in ["fast", "standard", "advanced"]:
                    if key in credits_config:
                        if not isinstance(credits_config[key], int) or credits_config[key] < 0:
                            self.add_error(
                                "credits_config",
                                f"{key} credit must be a positive integer"
                            )

                # --------------------------
                # Validate AUDIO (addon)
                # --------------------------
                audio = credits_config.get("audio")

                if audio:
                    if not isinstance(audio, dict):
                        self.add_error("credits_config", "audio must be an object")

                    else:
                        for mode, value in audio.items():
                            if mode not in ["fast", "standard", "advanced"]:
                                self.add_error(
                                    "credits_config",
                                    f"Invalid audio mode: {mode}"
                                )

                            if not isinstance(value, int) or value < 0:
                                self.add_error(
                                    "credits_config",
                                    f"Audio credit for {mode} must be positive integer"
                                )

            # SAVE mapping
            cleaned_data["model_mapping"] = {
                "fast": str(fast.id),
                "standard": str(standard.id),
                "advanced": str(advanced.id),
            }

        else:
            # clear mapping if not multi-mode
            cleaned_data["model_mapping"] = None

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        instance.model_mapping = self.cleaned_data.get("model_mapping")

        if commit:
            instance.save()
            self.save_m2m()

        return instance
       
class FeatureSettingInline(admin.TabularInline):
    model = FeatureSetting
    extra = 1
    ordering = ("mode", "display_order")

    fields = (
        "mode",
        "key",
        "type",
        "options",
        "default_value",
        "is_required",
        "display_order",
    )


# ==========================================================
# FEATURE ADMIN
# ==========================================================
@admin.register(Features)
class FeaturesAdmin(admin.ModelAdmin):

    form = FeatureAdminForm
    inlines = [FeatureSettingInline]

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))

        # remove if already present
        for f in ["fast_model", "standard_model", "advanced_model"]:
            if f in fields:
                fields.remove(f)

        # show only if multi-mode
        if obj and obj.is_multi_mode:
            fields += ["fast_model", "standard_model", "advanced_model"]

        if "model_mapping" in fields:
            fields.remove("model_mapping")

        return fields

    list_display = (
        "id",
        "name",
        "feature_type",
        "is_multi_mode",  
        "fast_credit_cost",
        "standard_credit_cost",
        "advanced_credit_cost",
        "is_premium",
        "is_active",
        "display_order",
        "created_at",
    )

    filter_horizontal = ("allowed_models",)
    ordering = ("display_order",)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return (
                "id",
                "feature_type",
                "created_at",
                "updated_at",
            )
        return ("id", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "default_model":
            kwargs["queryset"] = AIModel.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "allowed_models":
            kwargs["queryset"] = AIModel.objects.filter(is_active=True)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


# ==========================================================
# USER CREDITS ADMIN
# ==========================================================
@admin.register(UserCredits)
class UserCreditsAdmin(admin.ModelAdmin):

    list_display = (
        "user", "total_credits",
        "used_credits", "remaining_credits_display",
        "updated_at"
    )

    readonly_fields = ("used_credits", "created_at", "updated_at")

    def remaining_credits_display(self, obj):
        return obj.remaining_credits()

    # atomic credit add + transaction log
    @admin.action(description="Add 50 credits")
    def add_credits_50(self, request, queryset):

        for obj in queryset:
            obj.total_credits += 50
            obj.save()

            CreditTransaction.objects.create(
                user=obj.user,
                amount=50,
                transaction_type="credit",
                balance_after=obj.total_credits
            )

        self.message_user(request, "Credits added successfully")

    actions = ["add_credits_50"]


# ==========================================================
# CREDIT TRANSACTION ADMIN
# ==========================================================
@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):

    list_display = (
        "id", "user", "template",
        "feature", "amount",
        "transaction_type",
        "balance_after", "created_at"
    )

    readonly_fields = [f.name for f in CreditTransaction._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
from django.contrib import admin, messages
from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from django.db.models import F

from .models import Template, AIModel
from apps.features.models import Features
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

    class Meta:
        model = Features
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

        # -------------------------
        # Validate allowed models
        # -------------------------
        if allowed_models:
            if len(allowed_models) > 4:
                raise ValidationError("Maximum 4 models allowed per feature")

            for model in allowed_models:
                if model.feature_type != feature_type:
                    raise ValidationError(
                        f"{model.name} does not belong to {feature_type}"
                    )

        # -------------------------
        # Validate default model
        # -------------------------
        if default_model:
            if default_model not in allowed_models:
                raise ValidationError(
                    "Default model must be in allowed_models"
                )

            if default_model.feature_type != feature_type:
                raise ValidationError(
                    "Default model feature_type mismatch"
                )

        return cleaned_data


# ==========================================================
# FEATURE ADMIN
# ==========================================================
@admin.register(Features)
class FeaturesAdmin(admin.ModelAdmin):

    form = FeatureAdminForm

    list_display = (
        "id", "name", "feature_type",
        "is_premium", "is_active",
        "display_order", "created_at"
    )

    filter_horizontal = ("allowed_models",)
    ordering = ("display_order",)

    # Lock critical fields
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return (
                "id",
                "feature_type",   # cannot change
                "created_at",
                "updated_at",
            )
        return ("id", "created_at", "updated_at")

    # Disable add
    def has_add_permission(self, request):
        return False

    # Disable delete
    def has_delete_permission(self, request, obj=None):
        return False

    # -----------------------------
    # FILTER DEFAULT MODEL
    # -----------------------------
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "default_model":
            kwargs["queryset"] = AIModel.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # -----------------------------
    # FILTER ALLOWED MODELS
    # -----------------------------
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
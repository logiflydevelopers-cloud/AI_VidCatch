from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import format_html

from .models import Template, AIModel
from apps.services.firebase_storage import upload_file

# optional (if you implemented delete_file)
try:
    from apps.services.firebase_storage import delete_file
except:
    delete_file = None


# ============================
# ADMIN FORM (UPLOAD FIELDS)
# ============================

class TemplateAdminForm(forms.ModelForm):

    cover_image_file = forms.FileField(
        required=False,
        label="Upload Cover Image"
    )

    preview_files = forms.FileField(
        required=False,
        label="Upload Preview Images / Videos"
    )

    class Meta:
        model = Template
        fields = "__all__"


# ============================
# AI MODEL ADMIN
# ============================

@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "feature_type",
        "provider",
        "credit_cost",
        "is_default",
        "is_active",
    )

    list_filter = ("feature_type", "is_active")

    search_fields = ("name", "model_name")  # ✅ fixed


# ============================
# TEMPLATE ADMIN
# ============================

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):

    form = TemplateAdminForm

    list_display = (
        "id",
        "name",
        "preview_thumbnail",
        "category",
        "feature_type",
        "credit_cost",
        "is_active",
        "created_at",
    )

    list_filter = ("category", "feature_type", "is_active")

    search_fields = ("name",)

    filter_horizontal = ("allowed_models",)

    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        ("Basic Info", {
            "fields": (
                "id",
                "name",
                "category",
                "feature_type",
                "credit_cost",
                "is_active",
            )
        }),

        ("Media Upload", {
            "fields": (
                "cover_image_file",
                "preview_files",
            )
        }),

        ("Media URLs", {
            "fields": (
                "cover_image",
                "preview_media",
            )
        }),

        ("AI Configuration", {
            "fields": (
                "allowed_models",
                "default_model",
                "prompt_template",
                "input_schema",
                "default_settings",
            )
        }),

        ("Timestamps", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    # ============================
    # MULTIPLE FILE INPUT
    # ============================
    def get_form(self, request, obj=None, **kwargs):

        form = super().get_form(request, obj, **kwargs)

        if "preview_files" in form.base_fields:
            form.base_fields["preview_files"].widget.attrs["multiple"] = True

        return form

    # ============================
    # FILTER DEFAULT MODEL BY FEATURE
    # ============================
    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        if db_field.name == "default_model":

            obj_id = request.resolver_match.kwargs.get("object_id")

            if obj_id:
                try:
                    template = Template.objects.get(id=obj_id)
                    kwargs["queryset"] = AIModel.objects.filter(
                        feature_type=template.feature_type,
                        is_active=True
                    )
                except Template.DoesNotExist:
                    pass
            else:
                kwargs["queryset"] = AIModel.objects.filter(is_active=True)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # ============================
    # PREVIEW THUMBNAIL
    # ============================
    def preview_thumbnail(self, obj):
        if obj.cover_image:
            return format_html(
                '<img src="{}" style="height:50px;border-radius:6px;" />',
                obj.cover_image
            )
        return "-"

    preview_thumbnail.short_description = "Preview"

    # ============================
    # SAVE MODEL
    # ============================
    def save_model(self, request, obj, form, change):

        # Save first (needed for ID)
        super().save_model(request, obj, form, change)

        # ========================
        # VALIDATION (CRITICAL)
        # ========================
        if obj.default_model:

            if obj.default_model not in obj.allowed_models.all():
                raise ValidationError(
                    "Default model must be in allowed_models"
                )

            if obj.default_model.feature_type != obj.feature_type:
                raise ValidationError(
                    "Model feature_type must match template feature_type"
                )

        # ========================
        # COVER IMAGE
        # ========================
        cover_file = form.cleaned_data.get("cover_image_file")

        if cover_file:

            # delete old (optional)
            if obj.cover_image and delete_file:
                try:
                    delete_file(obj.cover_image)
                except:
                    pass

            path = f"templates/{obj.id}/cover"
            url = upload_file(cover_file, path)

            obj.cover_image = url

        # ========================
        # PREVIEW FILES
        # ========================
        preview_files = request.FILES.getlist("preview_files")

        if preview_files:

            urls = list(obj.preview_media or [])

            for file in preview_files:

                # validate file type
                if not file.content_type.startswith(("image/", "video/")):
                    continue

                path = f"templates/{obj.id}/previews"
                url = upload_file(file, path)

                urls.append(url)

            obj.preview_media = urls

        # Final save
        obj.save()
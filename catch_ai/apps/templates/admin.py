from django.contrib import admin
from django import forms

from .models import Template, AIModel
from apps.services.firebase_storage import upload_file


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

    search_fields = ("name", "model_key")


# ============================
# TEMPLATE ADMIN
# ============================

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):

    form = TemplateAdminForm

    list_display = (
        "id",
        "name",
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

    # MULTIPLE FILE INPUT
    def get_form(self, request, obj=None, **kwargs):

        form = super().get_form(request, obj, **kwargs)

        if "preview_files" in form.base_fields:
            form.base_fields["preview_files"].widget.attrs["multiple"] = True

        return form

    # SAVE MODEL
    def save_model(self, request, obj, form, change):

        # Always save first so Django creates the object and ID
        super().save_model(request, obj, form, change)

        # ------------------------
        # COVER IMAGE
        # ------------------------
        cover_file = form.cleaned_data.get("cover_image_file")

        if cover_file:
            path = f"templates/{obj.id}/cover"
            url = upload_file(cover_file, path)
            obj.cover_image = url

        # ------------------------
        # PREVIEW FILES
        # ------------------------
        preview_files = request.FILES.getlist("preview_files")

        if preview_files:

            # ensure list
            urls = list(obj.preview_media or [])

            for file in preview_files:
                path = f"templates/{obj.id}/previews"
                url = upload_file(file, path)
                urls.append(url)

            obj.preview_media = urls

        # Final save with updated URLs
        obj.save()
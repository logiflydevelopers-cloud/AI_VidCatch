from django.contrib import admin, messages
from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from django.db.models import F
from .models import Template, AIModel
from apps.features.models import Features
from apps.services.firebase_storage import upload_file
from django.contrib import admin
from apps.credits.models import UserCredits, CreditTransaction
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

    search_fields = ("name", "model_name") 


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

            # if obj.default_model.feature_type != obj.feature_type:
            #     raise ValidationError(
            #         "Model feature_type must match template feature_type"
            #     )

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


# ============================
# FEATURE ADMIN FORM
# ============================

class FeatureAdminForm(forms.ModelForm):

    class Meta:
        model = Features
        fields = "__all__"


# ============================
# FEATURE ADMIN
# ============================

@admin.register(Features)
class FeaturesAdmin(admin.ModelAdmin):

    form = FeatureAdminForm

    list_display = (
        "id",
        "name",
        "feature_type",
        "flow_type",   
        "credit_cost",
        "is_premium",
        "is_active",
        "display_order",
        "created_at",
    )

    list_filter = (
        "feature_type",
        "flow_type", 
        "is_active",
        "is_premium"
    )

    search_fields = ("name",)

    filter_horizontal = ("allowed_models",)

    readonly_fields = ("id", "created_at", "updated_at")

    ordering = ("display_order",)

    # ============================
    # DYNAMIC FIELDS (IMPORTANT)
    # ============================
    def get_fields(self, request, obj=None):
        fields = [
            "id",
            "name",
            "feature_type",
            "flow_type",
            "credit_cost",
            "is_premium",
            "is_active",
            "display_order",
            "allowed_models",
            "default_model",
            "input_schema",
            "default_settings",
            "created_at",
            "updated_at",
        ]

        # ALWAYS show template on add page
        if obj is None:
            fields.insert(4, "template")

        # Show template when editing and flow_type = template
        elif obj.flow_type == "template":
            fields.insert(4, "template")

        return fields

    # ============================
    # FILTER DEFAULT MODEL BY FEATURE TYPE
    # ============================
    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        if db_field.name == "default_model":

            obj_id = request.resolver_match.kwargs.get("object_id")

            if obj_id:
                try:
                    feature = Features.objects.get(id=obj_id)
                    kwargs["queryset"] = AIModel.objects.filter(
                        feature_type=feature.feature_type,
                        is_active=True
                    )
                except Features.DoesNotExist:
                    pass
            else:
                kwargs["queryset"] = AIModel.objects.filter(is_active=True)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # ============================
    # VALIDATION ON SAVE (ENHANCED)
    # ============================
    def save_model(self, request, obj, form, change):

        super().save_model(request, obj, form, change)

        # MODEL VALIDATION
        if obj.default_model:

            if obj.default_model not in obj.allowed_models.all():
                raise ValidationError(
                    "Default model must be in allowed_models"
                )

            # if obj.default_model.feature_type != obj.feature_type:
            #     raise ValidationError(
            #         "Model feature_type must match feature feature_type"
            #     )

        # TEMPLATE VALIDATION
        if obj.flow_type == "template" and not obj.template:
            raise ValidationError("Template is required for template flow")

        if obj.flow_type == "ai" and obj.template:
            raise ValidationError("AI flow should not have a template")

        obj.save()


# ============================
# USER CREDITS ADMIN
# ============================
@admin.register(UserCredits)
class UserCreditsAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "total_credits",
        "used_credits",
        "remaining_credits_display",
        "updated_at",
    )
    search_fields = ("user__username", "user__email")
    readonly_fields = ("used_credits", "created_at", "updated_at")

    list_filter = ("created_at", "updated_at")

    def remaining_credits_display(self, obj):
        return obj.remaining_credits()
    remaining_credits_display.short_description = "Remaining Credits"

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("used_credits", "user", "created_at", "updated_at")
        return ("used_credits", "created_at", "updated_at")

    # Prevent duplicate wallets (clean admin-safe way)
    def save_model(self, request, obj, form, change):
        if not change:
            if UserCredits.objects.filter(user=obj.user).exists():
                self.message_user(
                    request,
                    "This user already has a credit wallet.",
                    level=messages.ERROR
                )
                return
        super().save_model(request, obj, form, change)

    # Optimized bulk credit add (atomic)
    @admin.action(description="Add 50 credits")
    def add_credits_50(self, request, queryset):
        updated = queryset.update(total_credits=F("total_credits") + 50)
        self.message_user(request, f"{updated} users updated successfully.")

    actions = ["add_credits_50"]


# ============================
# CREDIT TRANSACTIONS ADMIN
# ============================
@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "template",    
        "feature",         
        "amount",
        "transaction_type",
        "balance_after",
        "created_at",
    )

    list_filter = (
        "transaction_type",
        "template",       
        "feature",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "description",
        "template__name", 
    )

    ordering = ("-created_at",)

    readonly_fields = [field.name for field in CreditTransaction._meta.fields]

    # Full audit lock
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
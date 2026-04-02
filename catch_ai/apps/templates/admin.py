from django.contrib import admin, messages
from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from django.db.models import F

from .models import Template, AIModel
from apps.features.models import Features, FeatureSetting
from apps.services.firebase_storage import upload_file

from apps.credits.models import UserCredits, CreditTransaction
from .models import GenerationConfig
from django.db import models

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

    # -----------------------------
    # MULTI MODE
    # -----------------------------
    fast_model = forms.ModelChoiceField(queryset=AIModel.objects.none(), required=False)
    standard_model = forms.ModelChoiceField(queryset=AIModel.objects.none(), required=False)
    advanced_model = forms.ModelChoiceField(queryset=AIModel.objects.none(), required=False)

    # -----------------------------
    # COLORIZE
    # -----------------------------
    bw_color_model = forms.ModelChoiceField(queryset=AIModel.objects.none(), required=False)
    recolor_model = forms.ModelChoiceField(queryset=AIModel.objects.none(), required=False)

    # -----------------------------
    # IMAGE TO VIDEO
    # -----------------------------
    one_fast_model = forms.ModelChoiceField(queryset=AIModel.objects.none(), required=False)
    one_standard_model = forms.ModelChoiceField(queryset=AIModel.objects.none(), required=False)
    one_advanced_model = forms.ModelChoiceField(queryset=AIModel.objects.none(), required=False)

    two_fast_model = forms.ModelChoiceField(queryset=AIModel.objects.none(), required=False)
    two_standard_model = forms.ModelChoiceField(queryset=AIModel.objects.none(), required=False)
    two_advanced_model = forms.ModelChoiceField(queryset=AIModel.objects.none(), required=False)

    class Meta:
        model = Features
        exclude = ("model_mapping",)
        widgets = {
            "input_schema": JSONEditorWidget,
            "credits_config": JSONEditorWidget,
        }

    # ==========================================================
    # INIT
    # ==========================================================
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        print("\n====== INIT START ======")
        print("RAW DATA:", self.data)

        # -----------------------------
        # QUERYSET
        # -----------------------------
        if self.data.get("allowed_models"):
            qs = AIModel.objects.filter(id__in=self.data.getlist("allowed_models"))
        elif self.instance and self.instance.pk:
            qs = self.instance.allowed_models.all()
        else:
            qs = AIModel.objects.filter(is_active=True)

        for field in [
            "fast_model", "standard_model", "advanced_model",
            "bw_color_model", "recolor_model",
            "one_fast_model", "one_standard_model", "one_advanced_model",
            "two_fast_model", "two_standard_model", "two_advanced_model",
        ]:
            if field in self.fields:
                self.fields[field].queryset = qs

        # -----------------------------
        # INITIAL VALUES
        # -----------------------------
        mapping = getattr(self.instance, "model_mapping", {}) or {}
        print("Initial mapping:", mapping)

        feature_type = self.data.get("feature_type") or getattr(self.instance, "feature_type", None)

        # COLORIZE INITIAL
        if mapping and feature_type == "colorize":
            self.fields["bw_color_model"].initial = qs.filter(id=mapping.get("bw_color")).first()
            self.fields["recolor_model"].initial = qs.filter(id=mapping.get("recolor")).first()

        # IMAGE TO VIDEO INITIAL
        if mapping and feature_type == "image_to_video":
            one = mapping.get("one_image", {})
            two = mapping.get("two_image", {})

            if one:
                self.fields["one_fast_model"].initial = qs.filter(id=one.get("fast")).first()
                self.fields["one_standard_model"].initial = qs.filter(id=one.get("standard")).first()
                self.fields["one_advanced_model"].initial = qs.filter(id=one.get("advanced")).first()

            if two:
                self.fields["two_fast_model"].initial = qs.filter(id=two.get("fast")).first()
                self.fields["two_standard_model"].initial = qs.filter(id=two.get("standard")).first()
                self.fields["two_advanced_model"].initial = qs.filter(id=two.get("advanced")).first()

        print("Feature Type INIT:", feature_type)

        is_multi_mode = (
            self.data.get("is_multi_mode") in ["on", "true", True]
            or (self.instance and self.instance.is_multi_mode)
        )

        print("Is Multi Mode INIT:", is_multi_mode)

        # -----------------------------
        # FIELD VISIBILITY
        # -----------------------------
        if not is_multi_mode:
            self.fields.pop("fast_model", None)
            self.fields.pop("standard_model", None)
            self.fields.pop("advanced_model", None)

        if feature_type != "colorize":
            self.fields.pop("bw_color_model", None)
            self.fields.pop("recolor_model", None)

        if feature_type != "image_to_video":
            for field in [
                "one_fast_model", "one_standard_model", "one_advanced_model",
                "two_fast_model", "two_standard_model", "two_advanced_model",
            ]:
                self.fields.pop(field, None)

        print("====== INIT END ======\n")

    # ==========================================================
    # CLEAN
    # ==========================================================
    def clean(self):
        cleaned_data = super().clean()

        feature_type = self.instance.feature_type
        is_multi_mode = cleaned_data.get("is_multi_mode")

        # -----------------------------
        # IMAGE TO VIDEO (NEW)
        # -----------------------------
        if feature_type == "image_to_video":
            print(">>> ENTER IMAGE TO VIDEO MODE")

            def build_group(prefix):
                fast = cleaned_data.get(f"{prefix}_fast_model")
                standard = cleaned_data.get(f"{prefix}_standard_model")
                advanced = cleaned_data.get(f"{prefix}_advanced_model")

                data = {}

                if fast:
                    data["fast"] = str(fast.id)
                if standard:
                    data["standard"] = str(standard.id)
                if advanced:
                    data["advanced"] = str(advanced.id)

                return data if data else None

            one_image = build_group("one")
            two_image = build_group("two")

            mapping = {}

            if one_image:
                mapping["one_image"] = one_image
            if two_image:
                mapping["two_image"] = two_image

            self.instance.model_mapping = mapping if mapping else None

        # -----------------------------
        # MULTI MODE
        # -----------------------------
        elif is_multi_mode:
            print(">>> ENTER MULTI MODE")

            fast = cleaned_data.get("fast_model")
            standard = cleaned_data.get("standard_model")
            advanced = cleaned_data.get("advanced_model")

            if fast and standard and advanced:
                self.instance.model_mapping = {
                    "fast": str(fast.id),
                    "standard": str(standard.id),
                    "advanced": str(advanced.id),
                }

        # -----------------------------
        # COLORIZE
        # -----------------------------
        elif feature_type == "colorize":
            print(">>> ENTER COLORIZE MODE")

            bw = cleaned_data.get("bw_color_model")
            recolor = cleaned_data.get("recolor_model")

            if bw and recolor:
                self.instance.model_mapping = {
                    "bw_color": str(bw.id),
                    "recolor": str(recolor.id),
                }

        # -----------------------------
        # NORMAL
        # -----------------------------
        else:
            self.instance.model_mapping = None

        return cleaned_data

    # ==========================================================
    # SAVE
    # ==========================================================
    def save(self, commit=True):
        instance = super().save(commit=False)

        print("\n====== FORM SAVE START ======")
        print("Instance mapping BEFORE save:", instance.model_mapping)

        if commit:
            instance.save()
            self.save_m2m()

        print("Instance mapping AFTER save:", instance.model_mapping)
        print("====== FORM SAVE END ======\n")

        return instance
    
class FeatureSettingInline(admin.TabularInline):
    model = FeatureSetting
    extra = 1
    ordering = ("mode", "display_order")

    fields = (
        "input_type", 
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

    # ==========================================================
    # FIELDSETS (CLEAN UI)
    # ==========================================================
    def get_fieldsets(self, request, obj=None):

        fieldsets = [
            ("Basic Info", {
                "fields": (
                    "id",
                    "name",
                    "feature_type",
                    "is_multi_mode",
                    "allowed_models",
                    "default_model",
                    "is_premium",
                    "is_active",
                )
            }),

            ("Credits", {
                "fields": (
                    "credit_cost",
                    "fast_credit_cost",
                    "standard_credit_cost",
                    "advanced_credit_cost",
                    "credits_config",
                )
            }),
        ]

        # -----------------------------
        # IMAGE TO VIDEO 
        # -----------------------------
        if obj and obj.feature_type == "image_to_video":
            fieldsets.append(("One Image Models", {
                "fields": (
                    "one_fast_model",
                    "one_standard_model",
                    "one_advanced_model",
                )
            }))
            fieldsets.append(("Two Image Models", {
                "fields": (
                    "two_fast_model",
                    "two_standard_model",
                    "two_advanced_model",
                )
            }))

        # -----------------------------
        # MULTI MODE
        # -----------------------------
        elif obj and obj.is_multi_mode:
            fieldsets.append(("Modes", {
                "fields": (
                    "fast_model",
                    "standard_model",
                    "advanced_model",
                )
            }))

        # -----------------------------
        # COLORIZE MODE
        # -----------------------------
        if obj and obj.feature_type == "colorize":
            fieldsets.append(("Colorize Models", {
                "fields": (
                    "bw_color_model",
                    "recolor_model",
                )
            }))

        # -----------------------------
        # META
        # -----------------------------
        fieldsets.append(("Meta", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }))

        return fieldsets

    # ==========================================================
    # LIST VIEW
    # ==========================================================
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

    # ==========================================================
    # READ ONLY
    # ==========================================================
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return (
                "id",
                "feature_type",
                "created_at",
                "updated_at",
            )
        return ("id", "created_at", "updated_at")

    # ==========================================================
    # PERMISSIONS
    # ==========================================================
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # ==========================================================
    # QUERYSET FILTERS
    # ==========================================================
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
    
class GenerationConfigAdminForm(forms.ModelForm):

    class Meta:
        model = GenerationConfig
        fields = "__all__"
        widgets = {
            "default_settings": JSONEditorWidget,
        }

    def clean(self):
        cleaned_data = super().clean()

        model = cleaned_data.get("model")
        feature_type = cleaned_data.get("feature_type")

        if model and model.feature_type != feature_type:
            raise ValidationError("Model feature_type must match config feature_type")

        return cleaned_data


@admin.register(GenerationConfig)
class GenerationConfigAdmin(admin.ModelAdmin):

    form = GenerationConfigAdminForm

    list_display = (
        "id",
        "name",
        "config_type",
        "feature_type",
        "model",
        "credits",   
        "is_active",
        "created_at",
    )

    list_filter = ("config_type", "feature_type", "is_active")

    search_fields = ("name",)

    readonly_fields = ("id", "created_at")

    fieldsets = (
        ("Basic Info", {
            "fields": ("id", "name", "config_type", "feature_type")
        }),
        ("AI Settings", {
            "fields": ("model", "prompt_template", "default_settings")
        }),
        ("Credits & Control", {
            "fields": ("credits", "is_active")
        }),
        ("Metadata", {
            "fields": ("created_at",)
        }),
    )

    # -----------------------------
    # FILTER MODEL BASED ON FEATURE
    # -----------------------------
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "model":
            kwargs["queryset"] = AIModel.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # -----------------------------
    # ENSURE SINGLE ACTIVE CONFIG
    # -----------------------------
    def save_model(self, request, obj, form, change):

        if obj.is_active:
            GenerationConfig.objects.filter(
                config_type=obj.config_type,
                is_active=True
            ).exclude(id=obj.id).update(is_active=False)

        super().save_model(request, obj, form, change)
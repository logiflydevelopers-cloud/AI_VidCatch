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

    fast_model = forms.ModelChoiceField(queryset=AIModel.objects.none(), required=False)
    standard_model = forms.ModelChoiceField(queryset=AIModel.objects.none(), required=False)
    advanced_model = forms.ModelChoiceField(queryset=AIModel.objects.none(), required=False)

    bw_color_model = forms.ModelChoiceField(queryset=AIModel.objects.none(), required=False)
    recolor_model = forms.ModelChoiceField(queryset=AIModel.objects.none(), required=False)

    class Meta:
        model = Features
        exclude = ("model_mapping",)   # ✅ IMPORTANT
        widgets = {
            "input_schema": JSONEditorWidget,
            "credits_config": JSONEditorWidget,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        print("\n====== INIT START ======")
        print("RAW DATA:", self.data)

        if self.data.get("allowed_models"):
            qs = AIModel.objects.filter(id__in=self.data.getlist("allowed_models"))
        elif self.instance and self.instance.pk:
            qs = self.instance.allowed_models.all()
        else:
            qs = AIModel.objects.filter(is_active=True)

        for field in ["fast_model", "standard_model", "advanced_model", "bw_color_model", "recolor_model"]:
            self.fields[field].queryset = qs

        mapping = getattr(self.instance, "model_mapping", {}) or {}
        print("Initial mapping:", mapping)

        if mapping:
            self.fields["bw_color_model"].initial = qs.filter(id=mapping.get("bw_color")).first()
            self.fields["recolor_model"].initial = qs.filter(id=mapping.get("recolor")).first()

        feature_type = self.data.get("feature_type") or getattr(self.instance, "feature_type", None)
        print("Feature Type INIT:", feature_type)

        is_multi_mode = (
            self.data.get("is_multi_mode") in ["on", "true", True]
            or (self.instance and self.instance.is_multi_mode)
        )
        print("Is Multi Mode INIT:", is_multi_mode)

        if not is_multi_mode:
            self.fields.pop("fast_model", None)
            self.fields.pop("standard_model", None)
            self.fields.pop("advanced_model", None)

        if feature_type != "colorize":
            self.fields.pop("bw_color_model", None)
            self.fields.pop("recolor_model", None)

        print("====== INIT END ======\n")

    def clean(self):
        cleaned_data = super().clean()
        allowed_models = cleaned_data.get("allowed_models") or []
        allowed_ids = [m.id for m in allowed_models]


        feature_type = self.instance.feature_type
        is_multi_mode = cleaned_data.get("is_multi_mode")

        # -----------------------------
        # MULTI MODE
        # -----------------------------
        if is_multi_mode:
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
        # COLORIZE MODE
        # -----------------------------
        elif feature_type == "colorize":
            print(">>> ENTER COLORIZE MODE")

            bw = cleaned_data.get("bw_color_model")
            recolor = cleaned_data.get("recolor_model")

            if bw and recolor:
                print("Setting COLORIZE mapping...")

                mapping = {
                    "bw_color": str(bw.id),
                    "recolor": str(recolor.id),
                }

                self.instance.model_mapping = mapping

        # -----------------------------
        # NORMAL
        # -----------------------------
        else:
            self.instance.model_mapping = None

        return cleaned_data

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

    fields = (
        "mode",
        "key",
        "type",
        "options",
        "default_value",
        "is_required"
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
        "created_at",
    )

    filter_horizontal = ("allowed_models",)

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
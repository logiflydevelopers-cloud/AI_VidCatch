from django import forms
from .models import Template


class TemplateAdminForm(forms.ModelForm):

    cover_image_file = forms.FileField(required=False)
    preview_files = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"multiple": True})
    )

    class Meta:
        model = Template
        fields = "__all__"
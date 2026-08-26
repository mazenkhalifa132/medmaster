from django.contrib import admin
from django import forms

from .models import WebsiteSettings


class WebsiteSettingsAdminForm(forms.ModelForm):
    class Meta:
        model = WebsiteSettings
        fields = ('unlock_all_features', 'lock_all_features')
        widgets = {
            'unlock_all_features': forms.CheckboxInput(attrs={
                'onclick': (
                    "var other=document.getElementById('id_lock_all_features');"
                    "if(this.checked){other.checked=false;}else if(!other.checked){this.checked=true;}"
                ),
            }),
            'lock_all_features': forms.CheckboxInput(attrs={
                'onclick': (
                    "var other=document.getElementById('id_unlock_all_features');"
                    "if(this.checked){other.checked=false;}else if(!other.checked){this.checked=true;}"
                ),
            }),
        }


@admin.register(WebsiteSettings)
class WebsiteSettingsAdmin(admin.ModelAdmin):
    form = WebsiteSettingsAdminForm
    fields = ('unlock_all_features', 'lock_all_features')

    def has_add_permission(self, request):
        return not WebsiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

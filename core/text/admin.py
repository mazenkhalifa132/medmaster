from django.contrib import admin
from django.forms import ModelForm, Select
from django.utils import timezone

from .models import TextContent, TextSubcategory
from .widgets import RichTextEditorWidget


class SubcategoryByModuleSelect(Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value and hasattr(value, 'instance'):
            option['attrs']['data-module'] = value.instance.module_id
        return option


class TextContentAdminForm(ModelForm):
    class Meta:
        model = TextContent
        fields = '__all__'
        widgets = {
            'subcategory': SubcategoryByModuleSelect,
            'content': RichTextEditorWidget,
        }

    class Media:
        js = ('text/admin/text_content_filters.js',)


@admin.register(TextContent)
class TextContentAdmin(admin.ModelAdmin):
    form = TextContentAdminForm
    list_display = ('title', 'subcategory', 'module', 'author', 'status', 'is_trial', 'created_at', 'updated_at')
    list_filter = ('module__year', 'module', 'subcategory', 'status', 'is_trial', 'author', 'created_at')
    search_fields = ('title', 'content', 'module__name')
    readonly_fields = ('author', 'created_at', 'updated_at')
    fields = ('title', 'module', 'subcategory', 'author', 'status', 'is_trial', 'content', 'created_at', 'updated_at')
    actions = ('publish_selected', 'move_to_draft')

    @admin.action(description='Publish selected text content')
    def publish_selected(self, request, queryset):
        queryset.update(status=TextContent.Status.PUBLISHED, updated_at=timezone.now())

    @admin.action(description='Move selected text content back to draft')
    def move_to_draft(self, request, queryset):
        queryset.update(status=TextContent.Status.DRAFT, updated_at=timezone.now())

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(TextSubcategory)
class TextSubcategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'module', 'order')
    list_filter = ('module__year', 'module')
    search_fields = ('name', 'module__name')
    ordering = ('module__year', 'module__order', 'order', 'name')

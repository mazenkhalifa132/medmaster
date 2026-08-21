from django.forms import Textarea
from django.urls import reverse


class RichTextEditorWidget(Textarea):
    template_name = 'text/widgets/rich_text_editor.html'

    class Media:
        css = {'all': ('text/admin/rich_text_editor.css',)}

    def get_context(self, name, value, attrs):
        attrs = attrs or {}
        context = super().get_context(name, value, attrs)
        context['widget']['upload_url'] = reverse('text-editor-upload-image')
        context['widget']['attrs']['class'] = 'rich-text-editor-source'
        return context

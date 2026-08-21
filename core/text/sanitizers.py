from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

from django.conf import settings


ALLOWED_TAGS = {
    'p', 'br', 'strong', 'b', 'em', 'i', 'u', 'mark', 'h1', 'h2', 'h3',
    'ul', 'ol', 'li', 'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th',
    'td', 'blockquote', 'hr', 'aside', 'span',
}
VOID_TAGS = {'br', 'hr', 'img'}
CALLOUT_CLASSES = {
    'medical-callout', 'medical-key-point', 'medical-clinical-pearl',
    'medical-warning', 'medical-clinical-case', 'medical-definition',
    'medical-diagnosis', 'medical-treatment', 'medical-pathophysiology',
}


def _safe_style(value):
    allowed = []
    for declaration in value.split(';'):
        property_name, separator, property_value = declaration.partition(':')
        if not separator:
            continue
        property_name = property_name.strip().lower()
        property_value = property_value.strip()
        if property_name == 'text-align' and property_value in {'left', 'center', 'right', 'justify'}:
            allowed.append(f'{property_name}: {property_value}')
        elif property_name in {'color', 'background-color'} and (
            property_value.startswith('#') or property_value.startswith('rgb(')
        ):
            allowed.append(f'{property_name}: {property_value}')
    return '; '.join(allowed)


class RichTextSanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            return
        safe_attrs = []
        attributes = dict(attrs)
        if tag == 'a':
            href = attributes.get('href', '')
            if urlparse(href).scheme in {'http', 'https', 'mailto'}:
                safe_attrs.append(('href', href))
                if attributes.get('target') == '_blank':
                    safe_attrs.extend((('target', '_blank'), ('rel', 'noopener noreferrer')))
        elif tag == 'img':
            src = attributes.get('src', '')
            if src.startswith(settings.MEDIA_URL):
                safe_attrs.append(('src', src))
                if attributes.get('alt'):
                    safe_attrs.append(('alt', attributes['alt']))
                for name in ('width', 'height'):
                    if attributes.get(name, '').isdigit():
                        safe_attrs.append((name, attributes[name]))
            else:
                return
        if tag == 'aside':
            classes = set(attributes.get('class', '').split()) & CALLOUT_CLASSES
            if classes:
                safe_attrs.append(('class', ' '.join(sorted(classes))))
        if tag in {'p', 'h1', 'h2', 'h3', 'span', 'th', 'td'}:
            style = _safe_style(attributes.get('style', ''))
            if style:
                safe_attrs.append(('style', style))
        attr_html = ''.join(f' {name}="{escape(value, quote=True)}"' for name, value in safe_attrs)
        self.parts.append(f'<{tag}{attr_html}>')

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in ALLOWED_TAGS and tag not in VOID_TAGS:
            self.parts.append(f'</{tag}>')

    def handle_data(self, data):
        self.parts.append(escape(data))


def sanitize_rich_text(value):
    sanitizer = RichTextSanitizer()
    sanitizer.feed(value or '')
    sanitizer.close()
    return ''.join(sanitizer.parts)

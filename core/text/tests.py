from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from modules.models import Module

from .models import TextContent, TextSubcategory


class TextContentTests(TestCase):
    def setUp(self):
        self.media_dir = TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(self.media_dir.cleanup)
        self.student = User.objects.create_user(username='student', password='StrongPass1')
        self.author = User.objects.create_superuser(
            username='author', email='author@example.com', password='StrongPass1'
        )
        self.module = Module.objects.create(
            year=1, name='Anatomy', image_url='https://example.com/anatomy.svg', has_text=True
        )

    def test_only_published_content_is_available_to_students(self):
        lectures = TextSubcategory.objects.create(module=self.module, name='Lectures', order=1)
        published = TextContent.objects.create(
            title='Published overview', module=self.module, author=self.author,
            subcategory=lectures, status=TextContent.Status.PUBLISHED,
            content='<p>Visible to students.</p>',
        )
        TextContent.objects.create(
            title='Private draft', module=self.module, author=self.author,
            status=TextContent.Status.DRAFT, content='<p>Not visible.</p>',
        )
        self.client.force_login(self.student)

        response = self.client.get(reverse('module-detail', args=[self.module.pk]))

        self.assertContains(response, published.title)
        self.assertNotContains(response, 'Private draft')
        self.assertEqual(response.context['text_groups'][0]['name'], 'Lectures')
        self.assertEqual(response.context['text_groups'][0]['text_contents'][0], published)

    def test_rich_text_is_sanitized_before_storage(self):
        content = TextContent.objects.create(
            title='Safe content', module=self.module, author=self.author,
            content='<p>Hello</p><script>alert(1)</script><a href="javascript:alert(1)">bad</a>',
        )

        self.assertNotIn('<script>', content.content)
        self.assertNotIn('javascript:', content.content)
        self.assertIn('<p>Hello</p>', content.content)

    def test_image_upload_requires_authorized_staff_and_valid_image(self):
        upload_url = reverse('text-editor-upload-image')
        self.client.force_login(self.student)
        self.assertIn(self.client.post(upload_url).status_code, (302, 403))

        self.client.force_login(self.author)
        invalid = SimpleUploadedFile('unsafe.txt', b'not an image', content_type='text/plain')
        self.assertEqual(self.client.post(upload_url, {'image': invalid}).status_code, 400)

        valid_png = SimpleUploadedFile(
            'diagram.png', b'\x89PNG\r\n\x1a\n' + b'valid-image-content', content_type='image/png'
        )
        response = self.client.post(upload_url, {'image': valid_png})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['url'].startswith('/media/text-content/'))

    def test_admin_uses_the_visual_editor_widget(self):
        self.client.force_login(self.author)

        response = self.client.get(reverse('admin:text_textcontent_add'))

        self.assertContains(response, 'rich-text-editor__toolbar')
        self.assertContains(response, 'rich_text_editor.js')
        self.assertContains(response, 'data-command="tableAction"')
        self.assertContains(response, 'data-command="deleteBlock"')

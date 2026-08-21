from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from files.models import FileSubcategory, StudyFile
from .models import Module


class ModuleFilesTests(TestCase):
    def test_files_are_grouped_by_subcategory(self):
        user = User.objects.create_user(username='student', password='StrongPass1')
        module = Module.objects.create(
            year=1,
            name='Anatomy',
            icon_class='bx-heart',
            has_files=True,
        )
        lectures = FileSubcategory.objects.create(module=module, name='Lectures', order=1)
        StudyFile.objects.create(
            year=1,
            module=module,
            subcategory=lectures,
            file_name='Upper limb lecture',
            file_size='2 MB',
            file_type='pdf',
            file_link='https://example.com/upper-limb.pdf',
        )
        StudyFile.objects.create(
            year=1,
            module=module,
            file_name='Revision sheet',
            file_size='1 MB',
            file_type='pdf',
            file_link='https://example.com/revision.pdf',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('module-detail', args=[module.pk]))

        self.assertEqual(response.context['total_files'], 2)
        self.assertEqual(response.context['file_groups'][0]['name'], 'Lectures')
        self.assertEqual(response.context['file_groups'][0]['files'][0].file_name, 'Upper limb lecture')
        self.assertEqual(response.context['file_groups'][1]['name'], 'Other files')


class ModuleAdminTests(TestCase):
    def test_module_colours_use_palette_inputs_in_admin(self):
        admin_user = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='StrongPass1'
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse('admin:modules_module_add'))

        self.assertContains(response, 'type="color" name="color"')
        self.assertContains(response, 'type="color" name="bg_color"')

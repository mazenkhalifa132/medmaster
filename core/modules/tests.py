from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from exams.models import Exam
from files.models import FileSubcategory, StudyFile
from .models import Module, ModuleExamSubject, ModuleExamWeek


class ModuleFilesTests(TestCase):
    def test_module_exams_can_be_filtered_by_subject_week_and_type(self):
        user = User.objects.create_user(username='student', password='StrongPass1')
        module = Module.objects.create(
            year=1, name='Anatomy', image_url='https://api.iconify.design/solar:heart-bold.svg'
        )
        subject = ModuleExamSubject.objects.create(module=module, name='Upper limb')
        week = ModuleExamWeek.objects.create(module=module, name='Week 1')
        exam = Exam.objects.create(
            year=1, module=module, subject=subject, week=week, name='Upper limb quiz',
            exam_type='practice', time_limit=20,
        )
        self.client.force_login(user)

        response = self.client.get(reverse('module-detail', args=[module.pk]))

        self.assertContains(response, 'id="exam-subject-filter"')
        self.assertContains(response, 'id="exam-week-filter"')
        self.assertContains(response, 'id="exam-type-filter"')
        self.assertContains(
            response,
            f'data-exam-row data-subject="{subject.pk}" data-week="{week.pk}" data-exam-type="practice"',
        )

    def test_module_exams_tab_shows_an_empty_state_when_no_exams_exist(self):
        user = User.objects.create_user(username='student', password='StrongPass1')
        module = Module.objects.create(
            year=1,
            name='Anatomy',
            image_url='https://api.iconify.design/solar:heart-bold.svg',
            has_exams=True,
        )
        self.client.force_login(user)

        response = self.client.get(reverse('module-detail', args=[module.pk]))

        self.assertContains(response, 'There are no exams available for this module yet.')

    def test_files_are_grouped_by_subcategory(self):
        user = User.objects.create_user(username='student', password='StrongPass1')
        module = Module.objects.create(
            year=1,
            name='Anatomy',
            image_url='https://api.iconify.design/solar:heart-bold.svg',
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
        self.assertContains(response, 'https://api.iconify.design/solar:heart-bold.svg?color=%233b82f6')


class ModuleAdminTests(TestCase):
    def test_module_colours_use_palette_inputs_in_admin(self):
        admin_user = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='StrongPass1'
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse('admin:modules_module_add'))

        self.assertContains(response, 'type="color" name="color"')
        self.assertContains(response, 'type="color" name="bg_color"')

    def test_module_icon_can_be_configured_from_an_image_url(self):
        module = Module.objects.create(
            year=1,
            name='Anatomy',
            image_url='https://api.iconify.design/solar:heart-bold.svg',
        )

        self.assertEqual(module.image_url, 'https://api.iconify.design/solar:heart-bold.svg')
        self.assertEqual(
            module.colored_image_url,
            'https://api.iconify.design/solar:heart-bold.svg?color=%233b82f6',
        )

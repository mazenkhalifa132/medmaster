from django.test import TestCase

from .admin import StudyFileAdminForm
from .models import FileSubcategory
from modules.models import Module


class StudyFileAdminFormTests(TestCase):
    def test_subcategory_options_include_their_module_id(self):
        module = Module.objects.create(year=1, name='Anatomy', image_url='https://example.com/anatomy.svg')
        subcategory = FileSubcategory.objects.create(module=module, name='Lectures')

        form_html = StudyFileAdminForm().as_p()

        self.assertIn(f'value="{subcategory.pk}" data-module="{module.pk}"', form_html)

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from exams.models import Exam
from files.models import StudyFile
from modules.models import Module
from osce.models import OSCEExam
from progress.models import Badge, StudentBadge
from text.models import TextContent
from videos.models import Video

from .models import Notification, NotificationBroadcast
from .services import send_broadcast


class NotificationSystemTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username='student', email='student@example.com', password='StrongPass1', academic_year=1,
        )
        self.other_student = User.objects.create_user(
            username='other', email='other@example.com', password='StrongPass1', academic_year=2,
        )
        self.staff = User.objects.create_superuser(
            username='staff', email='staff@example.com', password='StrongPass1'
        )

    def test_new_learning_content_notifies_only_students_in_its_year(self):
        module = Module.objects.create(year=1, name='Anatomy', image_url='https://example.com/anatomy.svg')
        Video.objects.create(year=1, module=module, name='Lecture', link='https://example.com/video')
        StudyFile.objects.create(
            year=1, module=module, file_name='Notes', file_size='1 MB',
            file_type='pdf', file_link='https://example.com/notes.pdf',
        )
        TextContent.objects.create(
            module=module, title='Reading', content='<p>Read this.</p>',
            status=TextContent.Status.PUBLISHED,
        )
        Exam.objects.create(year=1, module=module, name='Quiz', time_limit=10)
        OSCEExam.objects.create(year=1, module=module, name='Station', mcq_timer=10)

        self.assertEqual(Notification.objects.filter(recipient=self.student).count(), 6)
        self.assertEqual(Notification.objects.filter(recipient=self.other_student).count(), 0)
        self.assertEqual(Notification.objects.filter(recipient=self.staff).count(), 0)

    def test_badge_notification_is_private_to_the_student(self):
        badge = Badge.objects.create(
            name='High scorer', image_url='https://example.com/badge.png',
            rule_type=Badge.EXAM_SCORE, threshold=80,
        )
        StudentBadge.objects.create(student=self.student, badge=badge, source_key='test-badge')

        notification = Notification.objects.get(recipient=self.student)
        self.assertEqual(notification.kind, Notification.BADGE)
        self.assertEqual(notification.image_url, badge.colored_image_url)
        self.assertFalse(Notification.objects.filter(recipient=self.other_student).exists())

    def test_dismissed_and_expired_notifications_are_not_returned_to_the_bell(self):
        active = Notification.objects.create(
            recipient=self.student, kind=Notification.ANNOUNCEMENT, title='Active', message='Visible'
        )
        Notification.objects.create(
            recipient=self.student, kind=Notification.ANNOUNCEMENT, title='Expired', message='Hidden',
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        self.client.force_login(self.student)

        response = self.client.post(reverse('notifications-dismiss', args=[active.pk]))

        self.assertEqual(response.status_code, 200)
        active.refresh_from_db()
        self.assertIsNotNone(active.dismissed_at)
        response = self.client.get('/')
        self.assertEqual(response.context['active_notification_count'], 0)

    def test_active_notification_stays_visible_until_dismissed_or_expired(self):
        Notification.objects.create(
            recipient=self.student, kind=Notification.ANNOUNCEMENT, title='Active', message='Visible'
        )
        self.client.force_login(self.student)

        response = self.client.get('/')

        self.assertEqual(response.context['active_notification_count'], 1)

    def test_broadcast_reaches_every_active_user(self):
        broadcast = NotificationBroadcast.objects.create(title='Welcome', message='Hello everyone')
        send_broadcast(broadcast)

        self.assertEqual(Notification.objects.filter(title='Welcome').count(), 3)

    def test_broadcast_can_target_one_academic_year(self):
        self.student.academic_year = 2
        self.student.save(update_fields=('academic_year',))
        self.other_student.academic_year = 3
        self.other_student.save(update_fields=('academic_year',))
        broadcast = NotificationBroadcast.objects.create(
            title='Year 2 update', message='Hello Year 2', target_academic_year=2,
        )

        send_broadcast(broadcast)

        self.assertTrue(Notification.objects.filter(recipient=self.student, title='Year 2 update').exists())
        self.assertFalse(Notification.objects.filter(recipient=self.other_student, title='Year 2 update').exists())
        self.assertFalse(Notification.objects.filter(recipient=self.staff, title='Year 2 update').exists())

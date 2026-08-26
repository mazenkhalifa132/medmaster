from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from modules.models import Module

from .models import Video, VideoSubcategory, VideoWatch


class VideoSystemTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student', password='StrongPass1')
        self.module = Module.objects.create(
            year=1,
            name='Anatomy',
            image_url='https://example.com/anatomy.svg',
            has_videos=True,
        )
        self.subcategory = VideoSubcategory.objects.create(
            module=self.module,
            name='Lectures',
            order=1,
        )
        self.video = Video.objects.create(
            year=1,
            module=self.module,
            subcategory=self.subcategory,
            name='Upper limb lecture',
            description='An overview of upper limb anatomy.',
            link='https://youtu.be/ARZY2l8AN0U',
        )
        self.client.force_login(self.user)

    def test_videos_are_grouped_and_youtube_share_links_are_embeddable(self):
        response = self.client.get(reverse('module-detail', args=[self.module.pk]))

        self.assertEqual(response.context['video_groups'][0]['name'], 'Lectures')
        self.assertEqual(response.context['video_groups'][0]['videos'][0], self.video)
        self.assertEqual(self.video.embed_url, 'https://www.youtube.com/embed/ARZY2l8AN0U')

    def test_opening_a_video_marks_it_watched_once(self):
        response = self.client.post(reverse('video-mark-watched', args=[self.video.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['watched'])
        self.assertEqual(VideoWatch.objects.filter(student=self.user, video=self.video).count(), 1)

        self.client.post(reverse('video-mark-watched', args=[self.video.pk]))
        self.assertEqual(VideoWatch.objects.filter(student=self.user, video=self.video).count(), 1)

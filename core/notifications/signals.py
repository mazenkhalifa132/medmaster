from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from exams.models import Exam
from files.models import StudyFile
from modules.models import Module
from osce.models import OSCEExam
from progress.models import StudentBadge
from text.models import TextContent
from videos.models import Video

from .services import notify_badge_awarded, notify_students


def _module_url(module_id):
    return f'/modules/{module_id}/'


@receiver(post_save, sender=Module)
def notify_new_module(sender, instance, created, **kwargs):
    if created and instance.is_active:
        notify_students(
            title=f'New module: {instance.name}',
            message=f'Year {instance.year} now has a new module to study.',
            academic_year=instance.year,
            url=_module_url(instance.pk),
        )


@receiver(post_save, sender=Video)
def notify_new_video(sender, instance, created, **kwargs):
    if created:
        notify_students(
            title=f'New video: {instance.name}',
            message=f'A new video was added to {instance.module.name}.',
            academic_year=instance.year,
            url=_module_url(instance.module_id),
        )


@receiver(post_save, sender=StudyFile)
def notify_new_file(sender, instance, created, **kwargs):
    if created:
        notify_students(
            title=f'New file: {instance.file_name}',
            message=f'A new {instance.get_file_type_display()} file was added to {instance.module.name}.',
            academic_year=instance.year,
            url=_module_url(instance.module_id),
        )


@receiver(pre_save, sender=TextContent)
def remember_text_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    instance._previous_status = sender.objects.filter(pk=instance.pk).values_list('status', flat=True).first()


@receiver(post_save, sender=TextContent)
def notify_new_text(sender, instance, created, **kwargs):
    became_published = instance.status == TextContent.Status.PUBLISHED and (
        created or instance._previous_status != TextContent.Status.PUBLISHED
    )
    if became_published:
        notify_students(
            title=f'New text content: {instance.title}',
            message=f'New reading material was added to {instance.module.name}.',
            academic_year=instance.module.year,
            url=_module_url(instance.module_id),
        )


@receiver(post_save, sender=Exam)
def notify_new_exam(sender, instance, created, **kwargs):
    if created and instance.is_active:
        notify_students(
            title=f'New exam: {instance.name}',
            message=f'A new {instance.get_exam_type_display()} exam is available in {instance.module.name}.',
            academic_year=instance.year,
            url=_module_url(instance.module_id),
        )


@receiver(post_save, sender=OSCEExam)
def notify_new_osce_exam(sender, instance, created, **kwargs):
    if created and instance.is_active:
        notify_students(
            title=f'New OSCE: {instance.name}',
            message=f'A new OSCE assessment is available in {instance.module.name}.',
            academic_year=instance.year,
            url=_module_url(instance.module_id),
        )


@receiver(post_save, sender=StudentBadge)
def notify_new_badge(sender, instance, created, **kwargs):
    if created:
        notify_badge_awarded(student=instance.student, badge=instance.badge)

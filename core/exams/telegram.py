import json
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from dashboard.models import TelegramGroup

from .models import Exam, ExamActivationAnnouncement


def send_exam_activation_announcement(exam_id):
    """Send or retry the Telegram message for an activated exam."""
    now = timezone.now()
    with transaction.atomic():
        notice, _ = ExamActivationAnnouncement.objects.get_or_create(exam_id=exam_id)
        notice = ExamActivationAnnouncement.objects.select_for_update().get(pk=notice.pk)
        if notice.sent_at:
            return True
        if notice.last_attempt_at and notice.last_attempt_at > now - timedelta(minutes=5):
            return False
        notice.last_attempt_at = now
        notice.attempt_count += 1
        notice.save(update_fields=('last_attempt_at', 'attempt_count'))

    try:
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '').strip()
        if not token:
            raise RuntimeError('TELEGRAM_BOT_TOKEN is not configured.')

        exam = Exam.objects.select_related('module', 'subject').get(pk=exam_id)
        group = TelegramGroup.objects.filter(year=exam.year).first()
        if not group or not group.bot_chat_id.strip():
            raise RuntimeError(f'No Telegram bot chat ID is configured for Year {exam.year}.')

        message = '\n'.join((
            'New quiz has been added',
            f'Module: {exam.module.name}',
            f'Subject: {exam.subject.name if exam.subject else "—"}',
            f'Name: {exam.name}',
            'Best of luck...',
        ))
        payload = json.dumps({'chat_id': group.bot_chat_id.strip(), 'text': message}).encode('utf-8')
        request = Request(
            f'https://api.telegram.org/bot{token}/sendMessage',
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
        if not result.get('ok'):
            raise RuntimeError(result.get('description', 'Telegram rejected the message.'))
    except (HTTPError, URLError, TimeoutError, OSError, RuntimeError, Exam.DoesNotExist, ValueError) as error:
        ExamActivationAnnouncement.objects.filter(exam_id=exam_id, sent_at__isnull=True).update(
            last_error=str(error)[:2000],
        )
        return False

    ExamActivationAnnouncement.objects.filter(exam_id=exam_id, sent_at__isnull=True).update(
        sent_at=timezone.now(), last_error='',
    )
    return True

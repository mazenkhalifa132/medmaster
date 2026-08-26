from django.contrib.auth import get_user_model

from .models import Notification


def _create_for_users(users, *, kind, title, message, url='', image_url='', expires_at=None):
    return Notification.objects.bulk_create([
        Notification(
            recipient=user,
            kind=kind,
            title=title,
            message=message,
            url=url,
            image_url=image_url,
            expires_at=expires_at or Notification._meta.get_field('expires_at').get_default(),
        )
        for user in users
    ])


def notify_students(*, title, message, academic_year, url=''):
    User = get_user_model()
    students = User.objects.filter(
        role='student', is_active=True, is_staff=False, academic_year=academic_year,
    )
    return _create_for_users(students, kind=Notification.CONTENT, title=title, message=message, url=url)


def notify_badge_awarded(*, student, badge):
    return Notification.objects.create(
        recipient=student,
        kind=Notification.BADGE,
        title=f'Badge earned: {badge.name}',
        message=f'You earned the {badge.name} badge.',
        image_url=badge.image_url,
        url='/#progress',
    )


def send_broadcast(broadcast):
    User = get_user_model()
    users = User.objects.filter(is_active=True)
    if broadcast.target_academic_year != broadcast.ALL_YEARS:
        users = users.filter(academic_year=broadcast.target_academic_year)
    return _create_for_users(
        users,
        kind=Notification.ANNOUNCEMENT,
        title=broadcast.title,
        message=broadcast.message,
        url=broadcast.url,
        expires_at=broadcast.expires_at,
    )

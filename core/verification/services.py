from django.contrib.auth import get_user_model

from websitesettings.models import WebsiteSettings

from .models import StudentVerification, normalize_phone


def assign_activated_academic_years(activations):
    """Assign students to the year selected on their active verification."""
    years_by_phone = {
        normalize_phone(activation.phone): activation.activation_year
        for activation in activations
        if activation.is_active and activation.activation_year is not None
    }
    if not years_by_phone:
        return 0

    users_to_update = []
    for user in get_user_model().objects.exclude(phone__isnull=True).only(
        'pk', 'phone', 'academic_year'
    ):
        activation_year = years_by_phone.get(normalize_phone(user.phone))
        if activation_year is not None and user.academic_year != activation_year:
            user.academic_year = activation_year
            users_to_update.append(user)

    if users_to_update:
        get_user_model().objects.bulk_update(users_to_update, ['academic_year'])
    return len(users_to_update)


def notify_activated_students(activations):
    """Tell matching students which academic year has just been activated."""
    years_by_phone = {
        normalize_phone(activation.phone): activation.activation_year
        for activation in activations
        if activation.is_active and activation.activation_year is not None
    }
    if not years_by_phone:
        return 0

    from notifications.models import Notification

    notifications = [
        Notification(
            recipient=user,
            kind=Notification.ANNOUNCEMENT,
            title=f'Year {years_by_phone[normalize_phone(user.phone)]} activated',
            message=(
                f'Your access to Year {years_by_phone[normalize_phone(user.phone)]} '
                'learning content is now active.'
            ),
            url='/#courses',
        )
        for user in get_user_model().objects.exclude(phone__isnull=True).only('pk', 'phone')
        if normalize_phone(user.phone) in years_by_phone
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)
    return len(notifications)


def activation_status(request):
    """Expose whether the sidebar activation advertisement should be shown."""
    user = request.user
    return {
        'has_active_academic_year': bool(
            user.is_authenticated
            and user.academic_year
            and has_year_access(user, user.academic_year)
        ),
    }


def has_year_access(user, year):
    """Return whether a user may access non-trial content for ``year``."""
    if not user.is_authenticated:
        return False
    if WebsiteSettings.all_features_are_unlocked():
        return True
    if user.is_superuser or getattr(user, 'role', None) == 'admin':
        return True

    phone = normalize_phone(getattr(user, 'phone', ''))
    return bool(
        phone
        and getattr(user, 'academic_year', None) == year
        and StudentVerification.objects.filter(
            phone=phone,
            activation_year=year,
            is_active=True,
        ).exists()
    )


def can_access_content(user, content):
    """Trial content is public to authenticated students; all other content is year-gated."""
    year = getattr(content, 'year', None)
    if year is None:
        year = content.module.year
    return bool(getattr(content, 'is_trial', False) or has_year_access(user, year))


def available_content(queryset, user, year):
    """Return all content for an activated year, otherwise only trial items."""
    return queryset if has_year_access(user, year) else queryset.filter(is_trial=True)

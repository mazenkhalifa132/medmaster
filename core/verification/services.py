from .models import StudentVerification, normalize_phone


def has_year_access(user, year):
    """Return whether a user may access non-trial content for ``year``."""
    if not user.is_authenticated:
        return False
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

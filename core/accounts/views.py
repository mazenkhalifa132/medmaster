import re
import json
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.conf import settings
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .models import User


TURNSTILE_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'


def verify_turnstile(request):
    """Validate the one-time Turnstile token with Cloudflare."""
    token = request.POST.get('cf-turnstile-response', '')
    if not token or not settings.TURNSTILE_SECRET_KEY:
        return False

    payload = urlencode({
        'secret': settings.TURNSTILE_SECRET_KEY,
        'response': token,
        'remoteip': request.META.get('REMOTE_ADDR', ''),
    }).encode()
    try:
        verification_request = Request(TURNSTILE_VERIFY_URL, data=payload)
        with urlopen(verification_request, timeout=5) as response:
            result = json.loads(response.read().decode())
    except (URLError, OSError, ValueError, json.JSONDecodeError):
        return False

    return result.get('success', False) is True


def signup_error_response(request, error_message):
    """Show a signup error without discarding the non-sensitive form fields."""
    messages.error(request, error_message)
    return render(
        request,
        'accounts/auth.html',
        {
            'signup_active': True,
            'turnstile_site_key': settings.TURNSTILE_SITE_KEY,
            'signup_data': {
                'first_name': request.POST.get('first_name', '').strip(),
                'last_name': request.POST.get('last_name', '').strip(),
                'email': request.POST.get('email', '').strip(),
                'phone': request.POST.get('phone', '').strip(),
                'academic_year': request.POST.get('academic_year', '').strip(),
                'agree_terms': request.POST.get('agree_terms') == 'on',
            },
        },
        status=400,
    )


@require_http_methods(["GET", "POST"])
def auth_page(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'accounts/auth.html', {
        'request': request,
        'turnstile_site_key': settings.TURNSTILE_SITE_KEY,
    })


@require_http_methods(['GET'])
def terms_view(request):
    terms_text = Path(__file__).with_name('terms_source.txt').read_text(encoding='utf-8').rstrip('\n')
    return render(request, 'accounts/terms.html', {'terms_text': terms_text})


@require_http_methods(["POST"])
def signup_view(request):
    if request.method != 'POST':
        return redirect('auth')

    if not verify_turnstile(request):
        return signup_error_response(request, 'Please complete the security check and try again.')

    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    email = request.POST.get('email', '').strip().lower()
    phone = request.POST.get('phone', '').strip()
    academic_year = request.POST.get('academic_year', '').strip()
    role = 'student'
    password1 = request.POST.get('password1', '')
    password2 = request.POST.get('password2', '')
    agree_terms = request.POST.get('agree_terms')

    if not first_name or not last_name or not email or not phone or not password1 or not password2:
        return signup_error_response(request, 'Please fill in all required fields.')

    if not agree_terms:
        return signup_error_response(request, 'You must agree to the terms and conditions.')

    if password1 != password2:
        return signup_error_response(request, 'Passwords do not match.')

    if not re.search(r'[A-Z]', password1) or not re.search(r'[a-z]', password1) or not re.search(r'[0-9]', password1) or len(password1) < 8:
        return signup_error_response(request, 'Password must be at least 8 characters long and include uppercase, lowercase, and a number.')

    if User.objects.filter(email__iexact=email).exists():
        return signup_error_response(request, 'An account with this email already exists.')

    if User.objects.filter(phone=phone).exists():
        return signup_error_response(request, 'A user with this phone number already exists.')

    username = f"{first_name.lower()}{last_name.lower()}".replace(' ', '')
    base_username = username or email.split('@')[0]
    candidate = base_username
    counter = 1
    while User.objects.filter(username=candidate).exists():
        candidate = f'{base_username}{counter}'
        counter += 1

    try:
        user = User.objects.create_user(
            username=candidate,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            academic_year=int(academic_year) if academic_year.isdigit() else None,
            role=role,
        )
    except (ValidationError, ValueError) as exc:
        return signup_error_response(request, str(exc))

    if role == 'admin':
        user.is_staff = True
        user.save(update_fields=['is_staff'])

    auth_login(request, user)
    messages.success(request, 'Welcome to Med Master!')
    return redirect('home')


@require_http_methods(["POST"])
def login_view(request):

    if not verify_turnstile(request):
        messages.error(request, 'Please complete the security check and try again.')
        return redirect('auth')

    email = request.POST.get('email', '').strip().lower()
    password = request.POST.get('password', '')

    user = User.objects.filter(email__iexact=email).first()
    if user and user.check_password(password):
        auth_login(request, user)
        messages.success(request, f'Welcome back, {user.first_name or user.email}.')
        return redirect('home')

    messages.error(request, 'Invalid email or password.')
    return redirect('auth')


def logout_view(request):
    auth_logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('auth')


@login_required(login_url='auth')
@require_http_methods(['GET', 'POST'])
def profile_view(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()

        if not first_name or not last_name:
            messages.error(request, 'First name and last name are required.')
        else:
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.save(update_fields=['first_name', 'last_name'])
            messages.success(request, 'Your profile has been updated.')
            return redirect('profile')

    return render(request, 'accounts/profile.html')

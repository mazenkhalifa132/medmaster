import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 🔐 المفتاح السري (خليه زي ماهو)
SECRET_KEY = 'django-insecure-+bi+s=dzuv97e#d6*pmyaqkbb2#zsepy5j#25%cc1r-ju1qea5'

# ⚠️ وضع التصحيح (خليه True دلوقتي عشان نشوف الأخطاء لو حصلت)
DEBUG = False

ALLOWED_HOSTS = [
    'medmaster.online',
    'www.medmaster.online',
    'YOUR_VPS_IP',   # غيرها بالـ IP بتاعك
    'localhost',
    '127.0.0.1',
]

CSRF_TRUSTED_ORIGINS = [
    'https://medmaster.online',
    'https://www.medmaster.online',
]


# ----------------------------------------
# التطبيقات المثبتة (متغيرش فيها)
INSTALLED_APPS = [
    'nested_admin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dashboard',
    'accounts',
    'modules',
    'files',
    'videos',
    'text',
    'exams',
    'osce',
    'upcoming',
    'notes',
    'progress',
    'notifications.apps.NotificationsConfig',
    'verification.apps.VerificationConfig',
    'websitesettings.apps.WebsitesettingsConfig',
]

# ----------------------------------------
# الـ Middleware (متغيرش فيها)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.csrf',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'notifications.context_processors.notifications',
                'upcoming.context_processors.upcoming_events',
                'progress.context_processors.recent_badges',
                'verification.services.activation_status',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# ----------------------------------------
# 🗄️ إعدادات قاعدة البيانات (عدل كلمة السر هنا)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'medmaster_db',
        'USER': 'medmaster_user',
        'PASSWORD': 'Ma162008',   # 🔑 غيرها لو كنت غيرتها
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000  # أو أي رقم أكبر يناسبك
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50 ميجابايت
# ----------------------------------------
# التحقق من كلمات المرور (متغيرش فيها)
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ----------------------------------------
# اللغة والوقت
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ----------------------------------------
# الملفات الثابتة والوسائط
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = '/accounts/'
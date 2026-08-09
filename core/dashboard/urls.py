from django.urls import path

from .views import home
from .views import telegram_feed

urlpatterns = [
    path('', home, name='home'),
    path("api/telegram/", telegram_feed),
]

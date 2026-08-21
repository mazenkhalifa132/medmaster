from django.urls import path

from . import views


urlpatterns = [
    path('mark-seen/', views.mark_all_seen, name='notifications-mark-all-seen'),
]

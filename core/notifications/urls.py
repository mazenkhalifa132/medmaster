from django.urls import path

from . import views


urlpatterns = [
    path('mark-seen/', views.mark_all_seen, name='notifications-mark-all-seen'),
    path('<int:notification_id>/dismiss/', views.dismiss, name='notifications-dismiss'),
]

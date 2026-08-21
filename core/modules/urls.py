from django.urls import path

from .views import mark_video_watched, module_detail


urlpatterns = [
    path('<int:pk>/', module_detail, name='module-detail'),
    path('videos/<int:pk>/watched/', mark_video_watched, name='video-mark-watched'),
]

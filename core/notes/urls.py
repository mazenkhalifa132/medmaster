from django.urls import path

from .views import create_note, delete_note

urlpatterns = [
    path('create/', create_note, name='note-create'),
    path('<int:pk>/delete/', delete_note, name='note-delete'),
]

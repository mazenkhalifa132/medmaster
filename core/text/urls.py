from django.urls import path

from .views import upload_editor_image


urlpatterns = [
    path('editor/upload-image/', upload_editor_image, name='text-editor-upload-image'),
]

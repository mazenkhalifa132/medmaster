from django.urls import path

from .views import exam_detail, submit_exam

urlpatterns = [
    path('<int:pk>/', exam_detail, name='exam-detail'),
    path('<int:pk>/submit/', submit_exam, name='exam-submit'),
]

from django.urls import path

from .views import osce_detail, submit_osce

urlpatterns = [
    path('<int:pk>/', osce_detail, name='osce-detail'),
    path('<int:pk>/submit/', submit_osce, name='osce-submit'),
]

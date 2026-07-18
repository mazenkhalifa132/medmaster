from django.urls import path

from .views import module_detail


urlpatterns = [
    path('<int:pk>/', module_detail, name='module-detail'),
]

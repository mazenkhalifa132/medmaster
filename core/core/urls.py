from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('_nested_admin/', include('nested_admin.urls')),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('modules/', include('modules.urls')),
    path('exams/', include('exams.urls')),
    path('osce/', include('osce.urls')),
    path('notes/', include('notes.urls')),
    path('', include('dashboard.urls')),
]

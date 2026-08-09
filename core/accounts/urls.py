from django.urls import path

from .views import auth_page, login_view, logout_view, profile_view, signup_view

urlpatterns = [
    path('', auth_page, name='auth'),
    path('login/', login_view, name='login'),
    path('signup/', signup_view, name='signup'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),
]

from django.urls import path
from . import views

app_name = 'users'  # This sets the namespace for the users app

urlpatterns = [
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
]

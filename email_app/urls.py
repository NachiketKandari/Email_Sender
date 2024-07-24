from django.urls import path
from .views import send_email, google_login, oauth2callback, logout_view

urlpatterns = [
    path('', send_email, name='send_email'),  # Path for sending emails
    path('google-login/', google_login, name='google_login'),  # Path for Google OAuth2 login
    path('oauth2callback/', oauth2callback, name='oauth2callback'),  # Path for OAuth2 callback
    path('logout/', logout_view, name='logout'),  # Path for logging out
]

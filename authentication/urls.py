from django.urls import path, include
from authentication.views import login_view, register_view, logout_view, verification_view, request_password_recovery, reset_password
urlpatterns = [
    path('login/', login_view, name="login"),
    path('logout/', logout_view, name="logout"),
    path('register/', register_view, name="register"),
    path('verification/', verification_view, name="verification"),
    path('request_recovery/', request_password_recovery, name="request_recovery"),
    path('reset/', reset_password, name="reset_password")
]

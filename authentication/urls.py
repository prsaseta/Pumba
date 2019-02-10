from django.urls import path, include
from authentication.views import login_view, register_view, logout_view, verification_view, test_view
urlpatterns = [
    path('login/', login_view, name="login"),
    path('logout/', logout_view, name="logout"),
    path('register/', register_view, name="register"),
    path('verification/', verification_view, name="verification"),
    #path('test/', test_view, name="test")
]
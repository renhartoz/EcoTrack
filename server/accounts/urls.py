from django.urls import path

from accounts.views import (
    LoginView,
    LogoutView,
    MeView,
    RefreshView,
    RegisterDemoView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("register-demo/", RegisterDemoView.as_view(), name="register_demo"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
]

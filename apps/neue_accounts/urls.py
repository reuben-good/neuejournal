from django.urls import path

from . import views

app_name = "neue_accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("delete/", views.delete_view, name="delete"),
    path("verify/<uidb64>/", views.verify_message_view, name="verify_message"),
    path("activate/<uidb64>/<token>/", views.activate, name="activate"),
]

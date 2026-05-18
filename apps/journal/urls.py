"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path

from . import views

app_name = "journal"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("entry/create", views.create_entry, name="create-entry"),
    path("entry/months", views.fetch_entry_months, name="entry-months"),
    path(
        "entry/list/<int:year>/<int:month>/meta",
        views.fetch_entry_list_meta,
        name="entry-list-meta",
    ),
    path(
        "entry/list/<int:year>/<int:month>/<int:page>",
        views.fetch_entry_list,
        name="page-entry-list",
    ),
    path(
        "entry/list/<int:year>/<int:month>",
        views.fetch_entry_list,
        name="page-entry-list-default",
    ),
    path("entry/detail/<int:entry_id>", views.fetch_entry_detail, name="entry-detail"),
    path("entry/images/<int:entry_id>", views.fetch_entry_images, name="entry-images"),
    path("photo/<int:photo_id>", views.serve_photo, name="serve-photo"),
    path(
        "photo/<int:photo_id>/<str:token>",
        views.serve_photo_with_token,
        name="serve-photo-token",
    ),
    path("stickers/<int:sticker_id>", views.serve_sticker, name="serve-sticker"),
    path("blank-page", views.empty_page, name="blank-page"),
    path("panels/account/", views.account_panel, name="account_panel"),
    path("panels/journal/", views.journal_panel, name="journal_panel"),
    path("panels/sticker/", views.sticker_panel, name="sticker_panel"),
    path("journal/update", views.journal_settings, name="journal_settings"),
    path("onboarding/<int:step>", views.onboarding, name="onboarding"),
]

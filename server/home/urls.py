from django.urls import path, re_path

from .views import CurrentUserView, SPAView

urlpatterns = [
    path("me/", CurrentUserView.as_view(), name="current-user"),
    re_path(r'^(?!api|admin|media|static).*$', SPAView.as_view(), name='spa'),
]


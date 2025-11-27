"""
URL configuration for procure2pay project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
import mimetypes
import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import FileResponse, Http404
from django.urls import include, path, re_path
from django.views.static import serve
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from home.views import CurrentUserView

schema_view = get_schema_view(
    openapi.Info(
        title="Procure2Pay API",
        default_version="v1",
        description="API documentation for the Procure2Pay system.",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)


def serve_media(request, path):
    """
    Serve media files in production.
    This view serves files from MEDIA_ROOT regardless of DEBUG setting.
    """
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        content_type, _ = mimetypes.guess_type(file_path)
        return FileResponse(
            open(file_path, 'rb'),
            content_type=content_type or 'application/octet-stream'
        )
    raise Http404("File not found")


urlpatterns = [
    path('', include('home.urls')),
    path("admin/", admin.site.urls),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/me/", CurrentUserView.as_view(), name="current-user"),
    path("api/v1/", include("requests_app.urls")),
    path(
        "api/docs/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "api/redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
    # Serve media files in both development and production
    re_path(r'^media/(?P<path>.*)$', serve_media, name='serve_media'),
]

# In development, also use Django's static file serving
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

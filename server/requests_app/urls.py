from django.urls import include, path
from rest_framework import routers

from .views import NotificationViewSet, PurchaseRequestViewSet

router = routers.DefaultRouter()
router.register(r"requests", PurchaseRequestViewSet, basename="purchase-request")
router.register(r"notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("", include(router.urls)),
]

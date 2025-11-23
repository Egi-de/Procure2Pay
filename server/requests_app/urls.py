from django.urls import include, path
from rest_framework import routers

from .views import PurchaseRequestViewSet

router = routers.DefaultRouter()
router.register(r"requests_app", PurchaseRequestViewSet, basename="purchase-request")

urlpatterns = [
    path("", include(router.urls)),
]


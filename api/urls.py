from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerUIView
from .views import FloodZoneViewSet, RiverViewSet, RiskAssetViewSet

router = DefaultRouter()
router.register(r"flood-zones", FloodZoneViewSet, basename="floodzone")
router.register(r"rivers", RiverViewSet, basename="river")
router.register(r"risk-assets", RiskAssetViewSet, basename="riskasset")

urlpatterns = [
    path("", include(router.urls)),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerUIView.as_view(url_name="schema"), name="swagger-ui"),
]

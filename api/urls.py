from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from .views import FloodZoneViewSet, RiverViewSet, RiskAssetViewSet

# DefaultRouter auto-generates all the standard CRUD URLs for each ViewSet
router = DefaultRouter()
router.register(r"flood-zones", FloodZoneViewSet, basename="floodzone")
router.register(r"rivers", RiverViewSet, basename="river")
router.register(r"risk-assets", RiskAssetViewSet, basename="riskasset")

urlpatterns = [
    path("", include(router.urls)),
    # drf-spectacular generates the OpenAPI schema, Swagger UI serves it
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

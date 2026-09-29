from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from workshop import views
router = DefaultRouter()
for prefix, view in [('customers', views.CustomerViewSet), ('vehicles', views.VehicleViewSet), ('orders', views.OrderViewSet), ('items', views.ItemViewSet)]:
    router.register(prefix, view, basename=prefix)
urlpatterns = [path('', views.app), path('admin/', admin.site.urls), path('accounts/', include('django.contrib.auth.urls')), path('api/session/', views.session_info), path('api/schema/', SpectacularAPIView.as_view(), name='schema'), path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema')), path('api/', include(router.urls))]

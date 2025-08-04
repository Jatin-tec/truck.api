from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.api.urls')),
    path('api/trucks/', include('trucks.api.urls')),
    path('api/quotations/', include('quotations.api.urls')),
    path('api/orders/', include('orders.api.urls')),
    path('api/payments/', include('payments.api.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

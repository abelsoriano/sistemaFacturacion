from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static

from setting import settings


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('facturacion.urls')),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

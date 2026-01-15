from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('ophthalmologist.urls')),  # Incluye URLs de ophthalmologist
    path('administrator/', include('administrator.urls')),  # Incluye URLs de administrador
    path('exam/', include('exam.urls')),
    path('statistics/', include('statistic.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='accounts:login', permanent=False), name='home'),
    path('accounts/', include('accounts.urls')),
    path('projects/', include('projects.urls')),
    path('land-records/', include('land_records.urls')),
    path('surveys/', include('surveys.urls')),
    path('compensation/', include('compensation.urls')),
    path('objections/', include('objections.urls')),
    path('monitoring/', include('monitoring.urls')),
    path('notifications/', include('notifications.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

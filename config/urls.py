"""Root URL configuration for SharedSpace Philippines."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from apps.accounts import views as account_views
from apps.core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('properties/', include('apps.properties.urls')),
]

# Error handlers rendered from templates/errors/
handler403 = core_views.forbidden
handler404 = core_views.not_found
handler500 = core_views.server_error

from django.views.static import serve
from django.urls import re_path

# Serve uploaded media files
urlpatterns += [
    re_path(r'^media/verification_documents/(?P<path>.*)$', account_views.private_media),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]


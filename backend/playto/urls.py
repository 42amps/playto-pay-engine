from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("payouts.urls")),
]

# Serve React frontend in production
if not settings.DEBUG:
    urlpatterns += [
        path("", TemplateView.as_view(template_name="index.html")),
        path("<path:path>", TemplateView.as_view(template_name="index.html")),
    ]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

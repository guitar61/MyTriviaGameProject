from django.contrib import admin
from django.urls import path, include  # Import 'include' to link to other URL configurations

urlpatterns = [
    path('admin/', admin.site.urls),      # Existing admin route
    path('', include('webapp.urls')),     # Include the URLs for your webapp
]

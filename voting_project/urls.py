# voting_project/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Send all non-admin traffic to our voting_app's urls.py
    path('', include('voting_app.urls')),
    
    # Include Django's built-in auth URLs (for login/logout)
    path('accounts/', include('django.contrib.auth.urls')),
]

"""
URL configuration for myproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='Home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from django.urls import reverse_lazy
from django.views.generic import RedirectView
from users.views import root_redirect

urlpatterns = [
    path("", root_redirect, name="root"),
    path("client/", RedirectView.as_view(url=reverse_lazy("users:dashboard", kwargs={"role": "client"}), permanent=False), name="client"),
    path("vendor/", RedirectView.as_view(url=reverse_lazy("users:dashboard", kwargs={"role": "vendor"}), permanent=False), name="vendor"),
    path("users/", include("users.urls")),
    path("services/", include("services.urls")),
    path("events/", include("events.urls")),
    path("admin/", admin.site.urls),
]

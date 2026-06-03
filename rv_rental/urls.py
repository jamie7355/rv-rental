from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    # Override Django's login/logout to use dashboard flow
    path("accounts/login/", auth_views.LoginView.as_view(
        template_name="rentals/admin_login.html",
        next_page="/dashboard/",
    ), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page="/"), name="logout"),
    path("", include("rentals.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

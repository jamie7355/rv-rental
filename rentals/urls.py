from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("bookings/", views.admin_booking_list, name="admin_booking_list"),
    path("bookings/new/", views.admin_booking_create, name="admin_booking_create"),
    path("bookings/<int:pk>/", views.admin_booking_detail, name="admin_booking_detail"),
    path("bookings/<int:pk>/cancel/", views.admin_booking_cancel, name="admin_booking_cancel"),
    path("api/availability/<int:rv_id>/", views.availability_api, name="availability_api"),
]

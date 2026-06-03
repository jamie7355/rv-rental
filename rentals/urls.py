from django.urls import path
from . import views

urlpatterns = [
    # Customer-facing
    path("", views.home, name="home"),
    path("rv/<int:pk>/", views.rv_detail, name="rv_detail"),
    path("rv/<int:pk>/book/", views.rv_book, name="rv_book"),
    path("booking/<int:pk>/confirmed/", views.booking_confirmed, name="booking_confirmed"),

    # Admin panel
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("bookings/", views.admin_booking_list, name="admin_booking_list"),
    path("bookings/new/", views.admin_booking_create, name="admin_booking_create"),
    path("bookings/<int:pk>/", views.admin_booking_detail, name="admin_booking_detail"),
    path("bookings/<int:pk>/cancel/", views.admin_booking_cancel, name="admin_booking_cancel"),
    path("invoices/", views.admin_invoice_list, name="admin_invoice_list"),
    path("invoices/<int:pk>/", views.admin_invoice_detail, name="admin_invoice_detail"),
    path("invoices/<int:pk>/pdf/", views.admin_invoice_pdf, name="admin_invoice_pdf"),
    path("api/availability/<int:rv_id>/", views.availability_api, name="availability_api"),
    path("api/delivery-distance/", views.delivery_distance_api, name="delivery_distance_api"),
]

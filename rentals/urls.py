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
    path("bookings/<int:pk>/edit/", views.admin_booking_edit, name="admin_booking_edit"),
    path("bookings/<int:pk>/cancel/", views.admin_booking_cancel, name="admin_booking_cancel"),
    path("rvs/", views.admin_rv_list, name="admin_rv_list"),
    path("rvs/add/", views.admin_rv_add, name="admin_rv_add"),
    path("rvs/<int:pk>/edit/", views.admin_rv_edit, name="admin_rv_edit"),
    path("customers/", views.admin_customer_list, name="admin_customer_list"),
    path("customers/add/", views.admin_customer_add, name="admin_customer_add"),
    path("customers/<int:pk>/edit/", views.admin_customer_edit, name="admin_customer_edit"),
    path("settings/", views.admin_settings, name="admin_settings"),
    path("settings/change-password/", views.admin_change_password, name="admin_change_password"),
    path("settings/users/add/", views.admin_user_add, name="admin_user_add"),
    path("settings/users/<int:pk>/edit/", views.admin_user_edit, name="admin_user_edit"),
    path("quotes/", views.admin_quote_list, name="admin_quote_list"),
    path("quotes/new/", views.admin_quote_create, name="admin_quote_create"),
    path("quotes/<int:pk>/", views.admin_quote_detail, name="admin_quote_detail"),
    path("quotes/<int:pk>/convert/", views.admin_quote_convert, name="admin_quote_convert"),
    path("quotes/<int:pk>/pdf/", views.admin_quote_pdf, name="admin_quote_pdf"),
    path("invoices/", views.admin_invoice_list, name="admin_invoice_list"),
    path("invoices/<int:pk>/", views.admin_invoice_detail, name="admin_invoice_detail"),
    path("invoices/<int:pk>/pdf/", views.admin_invoice_pdf, name="admin_invoice_pdf"),
    path("api/availability/<int:rv_id>/", views.availability_api, name="availability_api"),
    path("api/delivery-distance/", views.delivery_distance_api, name="delivery_distance_api"),
]

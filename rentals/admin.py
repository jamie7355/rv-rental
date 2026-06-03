from django.contrib import admin
from .models import RV, Customer, Booking, Payment


@admin.register(RV)
class RVAdmin(admin.ModelAdmin):
    list_display = ["name", "capacity", "price_per_day", "damage_deposit", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name"]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["full_name", "email", "phone", "drivers_license_expiry", "created_at"]
    search_fields = ["first_name", "last_name", "email", "phone"]
    readonly_fields = ["created_at"]


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ["paid_at"]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ["customer", "rv", "start_date", "end_date", "status", "source", "rental_total", "damage_deposit"]
    list_filter = ["status", "source", "rv"]
    search_fields = ["customer__first_name", "customer__last_name", "customer__email"]
    readonly_fields = ["created_at", "updated_at", "num_days", "total_charged"]
    inlines = [PaymentInline]
    fieldsets = [
        ("Booking Details", {
            "fields": ["rv", "customer", "start_date", "end_date", "num_days", "status", "source", "created_by"]
        }),
        ("Financials", {
            "fields": ["rental_total", "damage_deposit", "total_charged"]
        }),
        ("Notes", {
            "fields": ["special_requests"]
        }),
        ("Timestamps", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"]
        }),
    ]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["booking", "amount", "payment_type", "method", "paid_at"]
    list_filter = ["method", "payment_type"]
    readonly_fields = ["paid_at"]

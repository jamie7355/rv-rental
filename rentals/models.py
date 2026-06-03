from django.db import models
from django.contrib.auth.models import User


class RV(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    capacity = models.PositiveIntegerField(help_text="Number of people it sleeps")
    price_per_day = models.DecimalField(max_digits=8, decimal_places=2)
    damage_deposit = models.DecimalField(max_digits=8, decimal_places=2, default=500)
    image = models.ImageField(upload_to="rvs/", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Customer(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    drivers_license_number = models.CharField(max_length=50)
    drivers_license_expiry = models.DateField()
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=20)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    class BookingSource(models.TextChoices):
        ADMIN = "admin", "Admin"
        ONLINE = "online", "Online"

    rv = models.ForeignKey(RV, on_delete=models.PROTECT, related_name="bookings")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="bookings")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    source = models.CharField(max_length=10, choices=BookingSource.choices, default=BookingSource.ADMIN)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    start_date = models.DateField()
    end_date = models.DateField()
    rental_total = models.DecimalField(max_digits=10, decimal_places=2)
    damage_deposit = models.DecimalField(max_digits=8, decimal_places=2)
    # Delivery
    is_delivery = models.BooleanField(default=False)
    delivery_address = models.TextField(blank=True)
    delivery_distance_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    delivery_charge = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Tax (applied to rental + delivery, not damage deposit)
    gst_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    pst_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    special_requests = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer} — {self.rv} ({self.start_date} to {self.end_date})"

    @property
    def num_days(self):
        return (self.end_date - self.start_date).days

    @property
    def taxable_subtotal(self):
        return self.rental_total + self.delivery_charge

    @property
    def total_charged(self):
        return self.rental_total + self.delivery_charge + self.gst_amount + self.pst_amount + self.damage_deposit

    class Meta:
        ordering = ["-created_at"]


class Payment(models.Model):
    class Method(models.TextChoices):
        STRIPE = "stripe", "Stripe (Online)"
        CASH = "cash", "Cash"
        CHEQUE = "cheque", "Cheque"
        ETRANSFER = "etransfer", "E-Transfer"

    class PaymentType(models.TextChoices):
        DEPOSIT = "deposit", "Deposit"
        FULL = "full", "Full Payment"
        DAMAGE_DEPOSIT = "damage_deposit", "Damage Deposit"
        REFUND = "refund", "Refund"

    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=Method.choices)
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices)
    stripe_payment_intent_id = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    paid_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_payment_type_display()} — ${self.amount} ({self.booking})"

from django import forms
from .models import Booking, Customer, RV


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            "first_name", "last_name", "email", "phone",
            "drivers_license_number", "drivers_license_expiry",
            "emergency_contact_name", "emergency_contact_phone", "notes",
        ]
        widgets = {
            "drivers_license_expiry": forms.DateInput(attrs={"type": "date"}),
        }


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["rv", "start_date", "end_date", "special_requests"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class AdminBookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["rv", "customer", "start_date", "end_date", "status", "special_requests"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

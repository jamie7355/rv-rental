from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages
from decimal import Decimal
from datetime import date
import json

from django.conf import settings as django_settings
from .models import RV, Booking, Customer
from .forms import AdminBookingForm, CustomerForm
from .utils import get_delivery_distance_km, calculate_delivery_charge, calculate_taxes


# ---------------------------------------------------------------------------
# Delivery distance API
# ---------------------------------------------------------------------------

def delivery_distance_api(request):
    """Calculate delivery distance and charge for a given address."""
    address = request.GET.get("address", "").strip()
    if not address:
        return JsonResponse({"error": "No address provided"}, status=400)

    distance_km = get_delivery_distance_km(address)
    if distance_km is None:
        return JsonResponse({"error": "Could not calculate distance. Please check the address."}, status=400)

    charge = calculate_delivery_charge(distance_km)
    return JsonResponse({
        "distance_km": float(distance_km),
        "charge": float(charge),
        "rate_per_km": django_settings.DELIVERY_RATE_PER_KM,
    })


# ---------------------------------------------------------------------------
# Customer-facing views
# ---------------------------------------------------------------------------

def home(request):
    rvs = RV.objects.filter(is_active=True)
    return render(request, "rentals/customer/home.html", {"rvs": rvs})


def rv_detail(request, pk):
    rv = get_object_or_404(RV, pk=pk, is_active=True)
    booked = Booking.objects.filter(
        rv=rv,
        status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
    ).values("start_date", "end_date")
    booked_json = json.dumps([
        {"start": str(b["start_date"]), "end": str(b["end_date"])} for b in booked
    ])
    return render(request, "rentals/customer/rv_detail.html", {
        "rv": rv,
        "booked_json": booked_json,
    })


def rv_book(request, pk):
    rv = get_object_or_404(RV, pk=pk, is_active=True)

    start_str = request.POST.get("start_date") or request.GET.get("start")
    end_str = request.POST.get("end_date") or request.GET.get("end")

    if not start_str or not end_str:
        return redirect("rv_detail", pk=pk)

    try:
        start_date = date.fromisoformat(start_str)
        end_date = date.fromisoformat(end_str)
    except ValueError:
        return redirect("rv_detail", pk=pk)

    num_days = (end_date - start_date).days
    if num_days <= 0:
        messages.error(request, "End date must be after start date.")
        return redirect("rv_detail", pk=pk)

    rental_total = rv.price_per_day * num_days
    grand_total = rental_total + rv.damage_deposit

    if request.method == "POST":
        form = CustomerForm(request.POST)
        is_delivery = request.POST.get("is_delivery") == "delivery"
        delivery_address = request.POST.get("delivery_address", "").strip()
        delivery_distance_km = None
        delivery_charge = 0

        if is_delivery and delivery_address:
            delivery_distance_km = get_delivery_distance_km(delivery_address)
            if delivery_distance_km:
                delivery_charge = calculate_delivery_charge(delivery_distance_km)

        gst, pst = calculate_taxes(rental_total, delivery_charge)
        grand_total = rental_total + delivery_charge + gst + pst + rv.damage_deposit

        if form.is_valid():
            customer, _ = Customer.objects.get_or_create(
                email=form.cleaned_data["email"],
                defaults={
                    "first_name": form.cleaned_data["first_name"],
                    "last_name": form.cleaned_data["last_name"],
                    "phone": form.cleaned_data["phone"],
                    "drivers_license_number": form.cleaned_data["drivers_license_number"],
                    "drivers_license_expiry": form.cleaned_data["drivers_license_expiry"],
                    "emergency_contact_name": form.cleaned_data["emergency_contact_name"],
                    "emergency_contact_phone": form.cleaned_data["emergency_contact_phone"],
                    "notes": form.cleaned_data.get("notes", ""),
                }
            )

            booking = Booking.objects.create(
                rv=rv,
                customer=customer,
                source=Booking.BookingSource.ONLINE,
                status=Booking.Status.PENDING,
                start_date=start_date,
                end_date=end_date,
                rental_total=rental_total,
                damage_deposit=rv.damage_deposit,
                is_delivery=is_delivery,
                delivery_address=delivery_address if is_delivery else "",
                delivery_distance_km=delivery_distance_km,
                delivery_charge=delivery_charge,
                gst_amount=gst,
                pst_amount=pst,
                special_requests=form.cleaned_data.get("notes", ""),
            )
            return redirect("booking_confirmed", pk=booking.pk)
    else:
        form = CustomerForm()
        gst, pst = calculate_taxes(rental_total, 0)
        grand_total = rental_total + gst + pst + rv.damage_deposit

    return render(request, "rentals/customer/book.html", {
        "rv": rv,
        "form": form,
        "start_date": start_date,
        "end_date": end_date,
        "num_days": num_days,
        "rental_total": rental_total,
        "grand_total": grand_total,
        "gst": gst,
        "pst": pst,
        "gst_rate": int(django_settings.GST_RATE * 100),
        "pst_rate": int(django_settings.PST_RATE * 100),
        "rate_per_km": django_settings.DELIVERY_RATE_PER_KM,
        "google_maps_api_key": django_settings.GOOGLE_MAPS_API_KEY,
    })


def booking_confirmed(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    return render(request, "rentals/customer/booking_confirmed.html", {"booking": booking})


def availability_api(request, rv_id):
    """Return booked date ranges for an RV as JSON."""
    rv = get_object_or_404(RV, pk=rv_id)
    bookings = Booking.objects.filter(
        rv=rv,
        status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
    ).values("start_date", "end_date")

    booked = [
        {"start": str(b["start_date"]), "end": str(b["end_date"])}
        for b in bookings
    ]
    return JsonResponse({"booked": booked})


@staff_member_required
def admin_dashboard(request):
    upcoming = Booking.objects.filter(
        status=Booking.Status.CONFIRMED
    ).select_related("rv", "customer").order_by("start_date")[:10]

    rvs = RV.objects.filter(is_active=True)
    return render(request, "rentals/admin_dashboard.html", {
        "upcoming": upcoming,
        "rvs": rvs,
    })


@staff_member_required
def admin_booking_create(request):
    rv_id = request.GET.get("rv")
    initial = {"rv": rv_id} if rv_id else {}

    if request.method == "POST":
        form = AdminBookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.created_by = request.user
            booking.source = Booking.BookingSource.ADMIN

            days = (booking.end_date - booking.start_date).days
            booking.rental_total = booking.rv.price_per_day * days
            booking.damage_deposit = booking.rv.damage_deposit
            booking.save()

            messages.success(request, f"Booking created for {booking.customer}.")
            return redirect("admin_dashboard")
    else:
        form = AdminBookingForm(initial=initial)

    rvs = RV.objects.filter(is_active=True)
    rv_availability = {rv.pk: [] for rv in rvs}
    for rv in rvs:
        booked = Booking.objects.filter(
            rv=rv,
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
        ).values("start_date", "end_date")
        rv_availability[rv.pk] = [
            {"start": str(b["start_date"]), "end": str(b["end_date"])}
            for b in booked
        ]

    return render(request, "rentals/admin_booking_create.html", {
        "form": form,
        "rv_availability_json": json.dumps(rv_availability),
    })


@staff_member_required
def admin_booking_list(request):
    bookings = Booking.objects.select_related("rv", "customer").all()
    status_filter = request.GET.get("status")
    rv_filter = request.GET.get("rv")

    if status_filter:
        bookings = bookings.filter(status=status_filter)
    if rv_filter:
        bookings = bookings.filter(rv_id=rv_filter)

    return render(request, "rentals/admin_booking_list.html", {
        "bookings": bookings,
        "rvs": RV.objects.filter(is_active=True),
        "status_choices": Booking.Status.choices,
        "selected_status": status_filter,
        "selected_rv": rv_filter,
    })


@staff_member_required
def admin_booking_detail(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    return render(request, "rentals/admin_booking_detail.html", {"booking": booking})


@staff_member_required
def admin_booking_cancel(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if request.method == "POST":
        booking.status = Booking.Status.CANCELLED
        booking.save()
        messages.success(request, "Booking cancelled.")
        return redirect("admin_booking_list")
    return render(request, "rentals/admin_booking_confirm_cancel.html", {"booking": booking})

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages
from decimal import Decimal
from datetime import date
import json

from django.conf import settings as django_settings
from django.http import HttpResponse
from .models import RV, Booking, Customer, Quote
from .forms import AdminBookingForm, CustomerForm
from .utils import get_delivery_distance_km, calculate_delivery_charge, calculate_taxes
from .invoice import generate_invoice_pdf


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
        delivery_charge = Decimal("0")

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
        gst, pst = calculate_taxes(rental_total, Decimal("0"))
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
def admin_quote_list(request):
    from django.utils import timezone
    quotes = Quote.objects.select_related("rv").all()
    # Auto-expire quotes past 24 hours
    for q in quotes:
        if q.status == Quote.Status.ACTIVE and timezone.now() > q.expires_at:
            q.status = Quote.Status.EXPIRED
            q.save(update_fields=["status"])
    quotes = Quote.objects.select_related("rv").all()
    return render(request, "rentals/admin_quote_list.html", {"quotes": quotes})


@staff_member_required
def admin_quote_create(request):
    from django.utils import timezone
    rvs = RV.objects.filter(is_active=True)
    rv_availability = {}
    for rv in rvs:
        booked = Booking.objects.filter(
            rv=rv, status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED]
        ).values("start_date", "end_date")
        rv_availability[rv.pk] = [
            {"start": str(b["start_date"]), "end": str(b["end_date"])} for b in booked
        ]

    if request.method == "POST":
        rv_id = request.POST.get("rv")
        rv = get_object_or_404(RV, pk=rv_id)
        start_date = date.fromisoformat(request.POST.get("start_date"))
        end_date = date.fromisoformat(request.POST.get("end_date"))
        num_days = (end_date - start_date).days
        is_delivery = request.POST.get("is_delivery") == "delivery"
        delivery_address = request.POST.get("delivery_address", "").strip()
        delivery_distance_km = None
        delivery_charge = Decimal("0")

        if is_delivery and delivery_address:
            delivery_distance_km = get_delivery_distance_km(delivery_address)
            if delivery_distance_km:
                delivery_charge = calculate_delivery_charge(delivery_distance_km)

        rental_total = rv.price_per_day * num_days
        gst, pst = calculate_taxes(rental_total, delivery_charge)

        quote = Quote.objects.create(
            rv=rv,
            created_by=request.user,
            customer_name=request.POST.get("customer_name", "").strip(),
            customer_email=request.POST.get("customer_email", "").strip(),
            customer_phone=request.POST.get("customer_phone", "").strip(),
            start_date=start_date,
            end_date=end_date,
            is_delivery=is_delivery,
            delivery_address=delivery_address if is_delivery else "",
            delivery_distance_km=delivery_distance_km,
            delivery_charge=delivery_charge,
            rental_total=rental_total,
            damage_deposit=rv.damage_deposit,
            gst_amount=gst,
            pst_amount=pst,
            notes=request.POST.get("notes", "").strip(),
        )
        messages.success(request, f"Quote #{quote.pk} created for {quote.customer_name}.")
        return redirect("admin_quote_detail", pk=quote.pk)

    return render(request, "rentals/admin_quote_create.html", {
        "rvs": rvs,
        "rv_availability_json": json.dumps(rv_availability),
        "rate_per_km": django_settings.DELIVERY_RATE_PER_KM,
        "google_maps_api_key": django_settings.GOOGLE_MAPS_API_KEY,
    })


@staff_member_required
def admin_quote_detail(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    return render(request, "rentals/admin_quote_detail.html", {"quote": quote})


@staff_member_required
def admin_quote_convert(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    if request.method == "POST" and quote.status == Quote.Status.ACTIVE:
        booking = Booking.objects.create(
            rv=quote.rv,
            created_by=request.user,
            source=Booking.BookingSource.ADMIN,
            status=Booking.Status.PENDING,
            start_date=quote.start_date,
            end_date=quote.end_date,
            rental_total=quote.rental_total,
            damage_deposit=quote.damage_deposit,
            is_delivery=quote.is_delivery,
            delivery_address=quote.delivery_address,
            delivery_distance_km=quote.delivery_distance_km,
            delivery_charge=quote.delivery_charge,
            gst_amount=quote.gst_amount,
            pst_amount=quote.pst_amount,
            special_requests=quote.notes,
            customer=_get_or_create_customer_from_quote(quote),
        )
        quote.status = Quote.Status.CONVERTED
        quote.converted_booking = booking
        quote.save()
        messages.success(request, f"Quote converted to Booking #{booking.pk}. Please complete the customer details.")
        return redirect("admin_booking_detail", pk=booking.pk)
    return redirect("admin_quote_detail", pk=pk)


def _get_or_create_customer_from_quote(quote):
    name_parts = quote.customer_name.strip().split(" ", 1)
    first = name_parts[0]
    last = name_parts[1] if len(name_parts) > 1 else ""
    customer, _ = Customer.objects.get_or_create(
        email=quote.customer_email,
        defaults={
            "first_name": first,
            "last_name": last,
            "phone": quote.customer_phone,
            "drivers_license_number": "PENDING",
            "drivers_license_expiry": quote.start_date,
            "emergency_contact_name": "PENDING",
            "emergency_contact_phone": "PENDING",
        }
    )
    return customer


@staff_member_required
def admin_quote_pdf(request, pk):
    from .invoice import generate_quote_pdf
    quote = get_object_or_404(Quote, pk=pk)
    buffer = generate_quote_pdf(quote)
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="quote-QT-{quote.pk:04d}.pdf"'
    return response


@staff_member_required
def admin_invoice_list(request):
    bookings = Booking.objects.select_related("rv", "customer").exclude(
        status=Booking.Status.CANCELLED
    ).order_by("-created_at")
    return render(request, "rentals/admin_invoice_list.html", {"bookings": bookings})


@staff_member_required
def admin_invoice_detail(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    return render(request, "rentals/admin_invoice_detail.html", {"booking": booking})


@staff_member_required
def admin_invoice_pdf(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    buffer = generate_invoice_pdf(booking)
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="invoice-INV-{booking.pk:04d}.pdf"'
    return response


@staff_member_required
def admin_booking_edit(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    rvs = RV.objects.filter(is_active=True)

    rv_availability = {}
    for rv in rvs:
        booked = Booking.objects.filter(
            rv=rv,
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED],
        ).exclude(pk=pk).values("start_date", "end_date")
        rv_availability[rv.pk] = [
            {"start": str(b["start_date"]), "end": str(b["end_date"])} for b in booked
        ]

    if request.method == "POST":
        is_delivery = request.POST.get("is_delivery") == "delivery"
        delivery_address = request.POST.get("delivery_address", "").strip()
        delivery_distance_km = None
        delivery_charge = Decimal("0")

        if is_delivery and delivery_address:
            delivery_distance_km = get_delivery_distance_km(delivery_address)
            if delivery_distance_km:
                delivery_charge = calculate_delivery_charge(delivery_distance_km)

        start_date = date.fromisoformat(request.POST.get("start_date"))
        end_date = date.fromisoformat(request.POST.get("end_date"))
        rv = get_object_or_404(RV, pk=request.POST.get("rv"))
        num_days = (end_date - start_date).days
        rental_total = rv.price_per_day * num_days
        gst, pst = calculate_taxes(rental_total, delivery_charge)

        booking.rv = rv
        booking.start_date = start_date
        booking.end_date = end_date
        booking.status = request.POST.get("status")
        booking.is_delivery = is_delivery
        booking.delivery_address = delivery_address if is_delivery else ""
        booking.delivery_distance_km = delivery_distance_km
        booking.delivery_charge = delivery_charge
        booking.rental_total = rental_total
        booking.damage_deposit = rv.damage_deposit
        booking.gst_amount = gst
        booking.pst_amount = pst
        booking.special_requests = request.POST.get("special_requests", "")

        # Update customer info
        customer = booking.customer
        customer.first_name = request.POST.get("first_name", "").strip()
        customer.last_name = request.POST.get("last_name", "").strip()
        customer.email = request.POST.get("email", "").strip()
        customer.phone = request.POST.get("phone", "").strip()
        customer.drivers_license_number = request.POST.get("drivers_license_number", "").strip()
        customer.drivers_license_expiry = request.POST.get("drivers_license_expiry")
        customer.emergency_contact_name = request.POST.get("emergency_contact_name", "").strip()
        customer.emergency_contact_phone = request.POST.get("emergency_contact_phone", "").strip()
        customer.notes = request.POST.get("customer_notes", "").strip()
        customer.save()
        booking.save()

        messages.success(request, "Booking updated successfully.")
        return redirect("admin_booking_detail", pk=booking.pk)

    return render(request, "rentals/admin_booking_edit.html", {
        "booking": booking,
        "rvs": rvs,
        "rv_availability_json": json.dumps(rv_availability),
        "status_choices": Booking.Status.choices,
        "rate_per_km": django_settings.DELIVERY_RATE_PER_KM,
    })


@staff_member_required
def admin_booking_cancel(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if request.method == "POST":
        booking.status = Booking.Status.CANCELLED
        booking.save()
        messages.success(request, "Booking cancelled.")
        return redirect("admin_booking_list")
    return render(request, "rentals/admin_booking_confirm_cancel.html", {"booking": booking})

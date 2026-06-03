from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages
from decimal import Decimal
import json

from .models import RV, Booking, Customer
from .forms import AdminBookingForm, CustomerForm


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

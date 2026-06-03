import requests
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings


def get_delivery_distance_km(destination_address):
    """
    Returns distance in km from Yorkton to the destination using Google Distance Matrix API.
    Returns None if the request fails.
    """
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": settings.DELIVERY_ORIGIN,
        "destinations": destination_address,
        "units": "metric",
        "key": settings.GOOGLE_MAPS_API_KEY,
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        element = data["rows"][0]["elements"][0]
        if element["status"] == "OK":
            distance_m = element["distance"]["value"]
            return Decimal(str(round(distance_m / 1000, 2)))
    except Exception:
        pass
    return None


def calculate_delivery_charge(distance_km):
    # Multiply by 2 for return trip (deliver to customer + retrieve camper)
    rate = Decimal(str(settings.DELIVERY_RATE_PER_KM))
    charge = Decimal(str(distance_km)) * 2 * rate
    return charge.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_taxes(rental_total, delivery_charge):
    taxable = Decimal(str(rental_total)) + Decimal(str(delivery_charge))
    gst = (taxable * Decimal(str(settings.GST_RATE))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    pst = (taxable * Decimal(str(settings.PST_RATE))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return gst, pst

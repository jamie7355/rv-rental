import requests
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
            return round(distance_m / 1000, 2)
    except Exception:
        pass
    return None


def calculate_delivery_charge(distance_km):
    # Multiply by 2 for return trip (deliver to customer + retrieve camper)
    return round(float(distance_km) * 2 * settings.DELIVERY_RATE_PER_KM, 2)


def calculate_taxes(rental_total, delivery_charge):
    taxable = float(rental_total) + float(delivery_charge)
    gst = round(taxable * settings.GST_RATE, 2)
    pst = round(taxable * settings.PST_RATE, 2)
    return gst, pst

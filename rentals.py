"""RV Rental booking system."""

AVAILABLE_RVS = [
    {"id": 1, "name": "Coachmen Freelander", "capacity": 4, "price_per_day": 150},
    {"id": 2, "name": "Winnebago Minnie", "capacity": 2, "price_per_day": 120},
    {"id": 3, "name": "Thor Chateau", "capacity": 6, "price_per_day": 200},
]


def list_available_rvs():
    """Return all available RVs."""
    return AVAILABLE_RVS


def calculate_total(rv_id, days):
    """Calculate total cost for renting an RV."""
    rv = next((r for r in AVAILABLE_RVS if r["id"] == rv_id), None)
    if rv is None:
        raise ValueError(f"RV with id {rv_id} not found")
    return rv["price_per_day"] * days


def make_booking(customer_name, rv_id, days):
    """Create a new booking."""
    total = calculate_total(rv_id, days)
    return {
        "customer": customer_name,
        "rv_id": rv_id,
        "days": days,
        "total": total,
    }

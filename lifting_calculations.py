import math


def perform_calculations(
    load_weight,
    center_of_gravity,
    equipment_specs,
    environmental_conditions,
    load_factor,
    number_of_load_bearing_legs,
    sling_angle_degrees,
    rated_capacity_per_leg,
):
    """Screen equal-share sling-leg loading; this is not lift approval."""
    try:
        load_weight = float(load_weight)
        center_of_gravity = float(center_of_gravity)
        load_factor = float(load_factor)
        sling_angle_degrees = float(sling_angle_degrees)
        rated_capacity_per_leg = float(rated_capacity_per_leg)
        number_of_load_bearing_legs = int(number_of_load_bearing_legs)
    except (TypeError, ValueError) as exc:
        raise ValueError("Enter valid numeric values for all lift calculations.") from exc

    values = (load_weight, center_of_gravity, load_factor, sling_angle_degrees, rated_capacity_per_leg)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Calculation values must be finite numbers.")

    if load_weight <= 0 or center_of_gravity <= 0 or rated_capacity_per_leg <= 0:
        raise ValueError("Load, center of gravity, and rated capacity must be greater than zero.")
    if load_factor < 1:
        raise ValueError("Load factor must be at least 1.0.")
    if number_of_load_bearing_legs < 1:
        raise ValueError("At least one load-bearing leg is required.")
    if not 0 < sling_angle_degrees <= 90:
        raise ValueError("Sling angle must be greater than 0 and no more than 90 degrees.")

    design_load = load_weight * load_factor
    angle_radians = math.radians(sling_angle_degrees)
    estimated_leg_load = design_load / (number_of_load_bearing_legs * math.sin(angle_radians))
    utilization = estimated_leg_load / rated_capacity_per_leg

    return {
        "load_weight_t": round(load_weight, 3),
        "center_of_gravity_m": round(center_of_gravity, 3),
        "equipment_specs": equipment_specs or "Not provided",
        "environmental_conditions": environmental_conditions or "Not provided",
        "load_factor": round(load_factor, 3),
        "number_of_load_bearing_legs": number_of_load_bearing_legs,
        "sling_angle_degrees": round(sling_angle_degrees, 2),
        "rated_capacity_per_leg_t": round(rated_capacity_per_leg, 3),
        "estimated_leg_load_t": round(estimated_leg_load, 3),
        "utilization_percent": round(utilization * 100, 1),
        "capacity_check": "Within entered WLL" if utilization <= 1 else "Exceeds entered WLL",
        "status": "Preliminary screening only - competent-person review required",
        "limitations": (
            "Assumes equal load sharing between legs and symmetric sling geometry. "
            "Use WLL applicable to the actual hitch and angle. Does not assess load balance, "
            "rigging configuration, lifting points, structure, or site conditions."
        ),
    }

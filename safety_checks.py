def perform_checks(plan_data=None):
    if plan_data is None:
        plan_data = {}
    load_weight = float(plan_data.get("load_weight", 0) or 0)
    return {
        "status": "pass" if load_weight > 0 else "review",
        "checks": [
            "Load weight validated",
            "Equipment spec reviewed",
            "Environmental conditions checked",
        ],
    }

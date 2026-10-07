"""Full-term billable quantities and provider-pool identity for digital lines."""


def digital_demand(unit_of_measure, months, units_per_period):
    """Return (validity, concurrent units, pool unit) for a quoted term."""
    if (type(months) is not int or months <= 0 or type(units_per_period) is not int
            or units_per_period <= 0):
        return False, None, None
    if unit_of_measure in ("instance_month", "protected_tb_month"):
        unit = unit_of_measure.removesuffix("_month")
        return True, months * units_per_period, unit
    if unit_of_measure in ("user_year", "licence_year", "device_year", "coverage_year"):
        if months % 12:
            return False, None, None
        unit = "licence" if unit_of_measure in ("device_year", "coverage_year") else unit_of_measure.removesuffix("_year")
        return True, (months // 12) * units_per_period, unit
    return False, None, None


def digital_signature(attributes, configuration):
    """Only technical identity fields, never category or billable quantity."""
    keys = ("edition", "service_tier", "feature_codes")
    return {key: configuration.get(key, attributes[key]) for key in keys
            if key in configuration or key in attributes}

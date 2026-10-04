"""Physical component stock quantities for the initial synthetic catalogue."""

from decimal import Decimal, ROUND_CEILING


def whole_component_requirements(aggregate_theoretical_demand):
    """Round once per component after all selected builds have been combined."""
    if any(not isinstance(v, Decimal) or not v.is_finite() or v < 0
           for v in aggregate_theoretical_demand.values()):
        raise ValueError("component theoretical demand must be nonnegative finite Decimal")
    return {component: units.to_integral_value(rounding=ROUND_CEILING)
            for component, units in aggregate_theoretical_demand.items()}

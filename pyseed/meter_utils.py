"""Utilities for normalizing SEED meter usage responses."""

from __future__ import annotations

import math
from typing import Any

KBTU_PER_KWH = 3.412


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{field} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a finite number")
    return number


def annual_energy_from_meter_data(
    meter_data: dict[str, Any],
    year: int | None = None,
) -> dict[str, Any]:
    """Convert an annual SEED meter response into fuel totals in kBtu.

    Electricity readings are assumed to be kWh and natural-gas readings kBtu,
    matching SEED's meter usage response. When ``year`` is omitted, the latest
    available annual reading is selected.
    """
    usage = meter_data.get("usage", meter_data)
    readings = usage.get("readings") if isinstance(usage, dict) else None
    if not isinstance(readings, list) or not readings:
        raise ValueError("SEED meter response did not include annual readings")

    warnings: list[str] = []
    valid_readings = [row for row in readings if isinstance(row, dict)]
    if not valid_readings:
        raise ValueError("SEED meter response did not include valid annual readings")
    if year is None:
        selected = max(valid_readings, key=lambda row: _number(row.get("year"), "reading.year"))
        if len(valid_readings) > 1:
            warnings.append("No meter year was supplied; the latest available year was selected.")
    else:
        matches = [row for row in valid_readings if _number(row.get("year"), "reading.year") == year]
        if not matches:
            raise ValueError(f"No annual meter reading was available for year {year}")
        selected = matches[0]

    meters = meter_data.get("meters") or []
    meter_types: dict[str, str] = {}
    for meter in meters:
        if not isinstance(meter, dict):
            continue
        meter_type = meter.get("type")
        if not meter_type:
            continue
        alias = meter.get("alias")
        if alias:
            meter_types[str(alias)] = str(meter_type)
        meter_types[str(meter_type)] = str(meter_type)
    electricity = 0.0
    natural_gas = 0.0
    for alias, raw_value in selected.items():
        if alias == "year" or alias not in meter_types or raw_value is None:
            continue
        value = _number(raw_value, f"meter reading {alias!r}")
        meter_type = meter_types[alias].casefold()
        if meter_type.startswith("electric"):
            electricity += value * KBTU_PER_KWH
        elif "natural gas" in meter_type:
            natural_gas += value

    if electricity == 0:
        warnings.append("No electric meter usage was found for the selected year.")
    if natural_gas == 0:
        warnings.append("No natural-gas meter usage was found for the selected year.")
    selected_year = int(_number(selected.get("year"), "reading.year"))
    return {
        "year": selected_year,
        "energy_kbtu": {
            "electricity": electricity,
            "natural_gas": natural_gas,
            "total": electricity + natural_gas,
        },
        "warnings": warnings,
    }

"""Internal helpers shared by more than one analysis service module."""

from __future__ import annotations

from typing import Any

# Shared by BETTER and EUI: how the pipeline should select the meter readings
# used for the analysis.
METER_SELECTION_MODES: tuple[str, ...] = ("all", "date_range", "select_cycle")


def validate_meter_selection(configuration: dict[str, Any]) -> None:
    """Validate the shared 'select_meters' family of configuration keys used by BETTER and EUI."""
    mode = configuration.get("select_meters")
    if mode not in METER_SELECTION_MODES:
        raise ValueError(f"select_meters must be one of {METER_SELECTION_MODES}, got {mode!r}")
    if mode == "date_range":
        meter = configuration.get("meter") or {}
        if not meter.get("start_date") or not meter.get("end_date"):
            raise ValueError("meter_start_date and meter_end_date are required when select_meters='date_range'")
    elif mode == "select_cycle" and not configuration.get("cycle_id"):
        raise ValueError("cycle_id is required when select_meters='select_cycle'")

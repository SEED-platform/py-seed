"""EUI analysis: trailing 12-month Energy Use Intensity from meter data."""

from __future__ import annotations

from typing import Any

from pyseed.analyses._shared import METER_SELECTION_MODES, validate_meter_selection

SERVICE_EUI = "EUI"

DOC: dict[str, Any] = {
    "label": "EUI",
    "purpose": (
        "Computes trailing Energy Use Intensity (site EUI, kBtu/sqft/yr) for each selected property "
        "from its electricity meter readings and gross floor area. A lightweight screening analysis, "
        "often run before BETTER."
    ),
    "required_inputs": [
        "Gross floor area must be set on the property",
        "At least one electricity meter (grid, solar, wind, or unknown type) with readings",
    ],
    "configuration_schema": {
        "select_meters": {
            "type": "str",
            "required": True,
            "allowed": list(METER_SELECTION_MODES),
            "description": (
                "'all' uses the most recent 12 months ending at the latest reading; 'date_range' and "
                "'select_cycle' scope the analysis to an explicit window."
            ),
        },
        "meter": {
            "type": "dict",
            "required": "only when select_meters == 'date_range'",
            "keys": {"start_date": "str (MM-DD-YYYY)", "end_date": "str (MM-DD-YYYY)"},
        },
        "cycle_id": {
            "type": "int",
            "required": "only when select_meters == 'select_cycle'",
        },
    },
    "output_schema": {
        "analysis_property_view.parsed_results": {
            "Fractional EUI (kBtu/sqft)": "float",
            "Annual Coverage %": "float, % of the year with usable meter data",
            "Total Annual Meter Reading (kBtu)": "float",
            "Gross Floor Area (sqft)": "float",
        },
        "extra_data_columns_written": ["analysis_eui", "analysis_eui_coverage"],
        "highlights": ["Fractional EUI (kBtu/sqft)", "Annual Coverage (%)"],
    },
    "failure_modes": [
        "Properties with no gross floor area are skipped (invalid area)",
        "Properties with no usable electricity meter readings are skipped (invalid meter)",
        "select_meters outside 'all'/'date_range'/'select_cycle' fails validation",
        "No valid properties in the batch fails the whole analysis",
    ],
}


def build_eui_configuration(
    select_meters: str = "all",
    meter_start_date: str | None = None,
    meter_end_date: str | None = None,
    cycle_id: int | None = None,
) -> dict[str, Any]:
    """Build a validated configuration dict for an EUI analysis.

    Args:
        select_meters (str): one of METER_SELECTION_MODES ("all", "date_range", "select_cycle").
        meter_start_date (str | None): required when select_meters == "date_range" (MM-DD-YYYY).
        meter_end_date (str | None): required when select_meters == "date_range" (MM-DD-YYYY).
        cycle_id (int | None): required when select_meters == "select_cycle".

    Returns:
        dict: ready to pass as `configuration` to SeedClient.create_analysis(service="EUI", ...).
    """
    configuration: dict[str, Any] = {"select_meters": select_meters}
    if select_meters == "date_range":
        configuration["meter"] = {"start_date": meter_start_date, "end_date": meter_end_date}
    elif select_meters == "select_cycle":
        configuration["cycle_id"] = cycle_id

    validate_meter_selection(configuration)
    return configuration

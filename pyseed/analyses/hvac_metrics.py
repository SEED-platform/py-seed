"""HVAC Metrics analysis: HVAC inventory metrics derived from property Elements."""

from __future__ import annotations

from typing import Any

SERVICE_HVAC_METRICS = "HVAC Metrics"

DOC: dict[str, Any] = {
    "label": "HVAC Metrics",
    "purpose": (
        "Derives simple HVAC inventory metrics (total cooling capacity, dominant refrigerant type, "
        "total electrical service size, airflow per unit area) from a property's Element records."
    ),
    "required_inputs": [
        "Selected properties must have at least one Element record",
        "Element extra_data should include HVAC fields such as 'Nominal Cooling Cap. (Tons)', "
        "'Refrigerant Type', 'Eletrical Data - Max Fuse', and 'Supply - SA (CFM)'",
        "floor_area_column is optional but required for the per-area metric",
    ],
    "configuration_schema": {
        "floor_area_column": {
            "type": "int",
            "required": False,
            "description": "Column.id used as gross floor area for the airflow/tonnage-per-area metrics.",
        },
    },
    "output_schema": {
        "analysis_property_view.parsed_results": {
            "Total Nominal Cooling Capacity (tons)": "float",
            "AC tonnage coverage area (sqft/ton)": "float or 'NA' if no floor_area_column",
            "Main Refrigerant Type": "str",
            "Total HVAC Electric Service Size (Amps)": "float",
            "Airflow Rate per unit Area (cfm/sqft)": "float or 'NA' if no floor_area_column",
        },
        "extra_data_columns_written": [
            "total_nominal_cooling_capacity",
            "ac_tonnage_coverage_area",
            "main_refrigerant_type",
            "total_electric_data_max_fuse",
            "airflow_rate_per_unit_area",
        ],
    },
    "failure_modes": [
        "Selected properties with no Elements at all fail the analysis",
        "Missing floor_area_column results in 'NA' per-area metrics instead of a failure",
    ],
}


def build_hvac_metrics_configuration(floor_area_column_id: int | None = None) -> dict[str, Any]:
    """Build a configuration dict for an HVAC Metrics analysis.

    Args:
        floor_area_column_id (int | None): Column.id to use as gross floor area for the
            per-area metrics. If omitted, those metrics are reported as "NA".

    Returns:
        dict: ready to pass as `configuration` to SeedClient.create_analysis(service="HVAC Metrics", ...).
    """
    return {"floor_area_column": floor_area_column_id} if floor_area_column_id is not None else {}

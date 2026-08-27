"""EEEJ analysis: Energy Equity & Environmental Justice indicators by census tract."""

from __future__ import annotations

from typing import Any

SERVICE_EEEJ = "EEEJ"

DOC: dict[str, Any] = {
    "label": "Energy Equity & Environmental Justice (EEEJ)",
    "purpose": (
        "Maps each property to a 2010 U.S. Census tract (via coordinates or geocoded address) and "
        "attaches equity/environmental-justice indicators for that tract, including Disadvantaged "
        "Community (DAC) status, energy burden, and low-income status."
    ),
    "required_inputs": [
        "Either high-confidence latitude/longitude, or",
        "Enough address data to geocode: address_line_1 plus city/state or postal_code",
    ],
    "configuration_schema": {},
    "output_schema": {
        "analysis_property_view.parsed_results": {
            "2010 Census Tract": "str",
            "Latitude": "float",
            "Longitude": "float",
            "DAC": "bool",
            "Energy Burden and is Low Income": "bool",
            "Energy Burden Percentile": "float",
            "Low Income": "bool",
            "Share of Neighboring Disadvantaged Tracts": "float",
            "Number of Affordable Housing Locations in Tract": "int",
            "EJ Screen Report URL": "str",
        },
        "extra_data_columns_written": [
            "analysis_census_tract",
            "analysis_dac",
            "analysis_energy_burden_low_income",
            "analysis_energy_burden_percentile",
            "analysis_low_income",
            "analysis_share_neighbors_disadvantaged",
            "analysis_number_affordable_housing",
        ],
        "highlights": ["Census Tract", "DAC", "Low Income?"],
    },
    "failure_modes": [
        "Missing or low-confidence location data fails the property",
        "Unable to geocode the property's address fails the property",
        "Upstream census/EJScreen service errors fail the property with a message",
    ],
}


def build_eeej_configuration() -> dict[str, Any]:
    """Build a configuration dict for an EEEJ analysis (no configuration options exist)."""
    return {}

"""CO2 analysis: trailing annual average CO2e emissions from electricity use."""

from __future__ import annotations

from typing import Any

SERVICE_CO2 = "CO2"

DOC: dict[str, Any] = {
    "label": "Average Annual CO2",
    "purpose": (
        "Estimates trailing annual CO2e emissions (kgCO2e) from a property's electricity use, using "
        "eGRID subregion emission factors, and optionally writes the results back to the property's "
        "total GHG emissions fields."
    ),
    "required_inputs": [
        "Gross floor area must be set on the property",
        "At least one electricity meter (grid/unknown type) with readings",
        "Property must have an eGRID subregion code (egrid_subregion_code) resolvable",
    ],
    "configuration_schema": {
        "save_co2_results": {
            "type": "bool",
            "required": False,
            "default": False,
            "description": "If true, overwrite the property's total_ghg_emissions / total_ghg_emissions_intensity fields.",
        },
    },
    "output_schema": {
        "analysis_property_view.parsed_results": {
            "Average Annual CO2 (kgCO2e)": "float",
            "Annual Coverage %": "float",
            "Total Annual Meter Reading (MWh)": "float",
            "Total GHG Emissions Intensity (kgCO2e/ft2/year)": "float",
        },
        "extra_data_columns_written": ["analysis_co2", "analysis_co2_coverage"],
        "property_fields_written_if_save_co2_results": [
            "total_ghg_emissions (MtCO2e)",
            "total_ghg_emissions_intensity",
        ],
        "highlights": ["Average Annual CO2 (kgCO2e)", "Annual Coverage (%)"],
    },
    "failure_modes": [
        "Properties with no meter data are skipped",
        "Properties missing an eGRID subregion code error out",
        "An eGRID subregion/year combination with no known emission factor errors out",
    ],
}


def build_co2_configuration(save_co2_results: bool = False) -> dict[str, Any]:
    """Build a configuration dict for a CO2 (Average Annual CO2) analysis.

    Args:
        save_co2_results (bool): if true, SEED overwrites the property's total_ghg_emissions and
            total_ghg_emissions_intensity fields with the analysis results.

    Returns:
        dict: ready to pass as `configuration` to SeedClient.create_analysis(service="CO2", ...).
    """
    return {"save_co2_results": save_co2_results}

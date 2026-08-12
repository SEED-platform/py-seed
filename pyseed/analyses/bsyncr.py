"""BSyncr analysis: change-point regression models via the external BSyncr web service."""

from __future__ import annotations

from typing import Any

SERVICE_BSYNCR = "BSyncr"

BSYNCR_MODEL_TYPES: tuple[str, ...] = (
    "Simple Linear Regression",
    "Three Parameter Linear Model Cooling",
    "Three Parameter Linear Model Heating",
    "Four Parameter Linear Model",
)

DOC: dict[str, Any] = {
    "label": "BSyncr",
    "purpose": (
        "Fits a change-point regression model (via the external BSyncr service) that relates a "
        "property's electricity use to outdoor air temperature, returning BuildingSync-formatted "
        "model coefficients and a plot. Useful for degree-day-normalized energy modeling."
    ),
    "required_inputs": [
        "Property latitude and longitude",
        "At least one linked electricity meter with 12+ readings and no null reading values",
    ],
    "configuration_schema": {
        "model_type": {
            "type": "str",
            "required": True,
            "allowed": list(BSYNCR_MODEL_TYPES),
            "description": "Regression model form to fit against electricity use vs. temperature.",
        },
    },
    "output_schema": {
        "analysis_property_view.parsed_results": {
            "models": "list of parsed <Model> elements from the returned BuildingSync XML",
        },
        "analysis_output_files": [
            "content_type=BuildingSync (.xml model file)",
            "content_type=PNG (plot image)",
        ],
        "highlights": [{"name": "Completed", "value": ""}],
    },
    "failure_modes": [
        "Missing BSYNCR_SERVER_HOST server setting fails the analysis immediately",
        "Invalid or missing model_type fails validation before running",
        "Properties missing lat/lng or usable meter readings are skipped with a warning",
        "No usable properties in the batch fails the whole analysis",
    ],
}


def build_bsyncr_configuration(model_type: str = "Simple Linear Regression") -> dict[str, Any]:
    """Build a validated configuration dict for a BSyncr analysis.

    Args:
        model_type (str): one of BSYNCR_MODEL_TYPES.

    Returns:
        dict: ready to pass as `configuration` to SeedClient.create_analysis(service="BSyncr", ...).
    """
    if model_type not in BSYNCR_MODEL_TYPES:
        raise ValueError(f"model_type must be one of {BSYNCR_MODEL_TYPES}, got {model_type!r}")
    return {"model_type": model_type}

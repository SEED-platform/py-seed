"""Element Statistics analysis: condition-index roll-ups by Uniformat category."""

from __future__ import annotations

from typing import Any

SERVICE_ELEMENT_STATISTICS = "Element Statistics"

DOC: dict[str, Any] = {
    "label": "Element Statistics",
    "purpose": (
        "Aggregates condition-index statistics for a property's Elements (building systems/equipment "
        "records) by Uniformat category, and flags whether the property has D.D.C. (direct digital "
        "control / building automation) control panels."
    ),
    "required_inputs": [
        "Selected properties must have Element records with Uniformat classification codes",
    ],
    "configuration_schema": {},
    "output_schema": {
        "analysis_property_view.parsed_results": {
            "<Uniformat category> CI": "float, average condition index for that category",
            "Has D.D.C Control Panels": "bool",
        },
        "extra_data_columns_written": "one column per '<category> CI' key, plus 'Has D.D.C Control Panels'",
        "highlights": "every result key/value pair, numeric values rounded to 2 decimals",
    },
    "failure_modes": [
        "Properties with no Elements produce empty/near-empty results",
        "Columns that cannot be created for the org are skipped rather than failing the run",
    ],
}


def build_element_statistics_configuration() -> dict[str, Any]:
    """Build a configuration dict for an Element Statistics analysis (no configuration options exist)."""
    return {}

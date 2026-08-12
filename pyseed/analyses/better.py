"""BETTER analysis: LBNL BETTER savings-potential estimation and ECM recommendations."""

from __future__ import annotations

from typing import Any

from pyseed.analyses._shared import METER_SELECTION_MODES, validate_meter_selection

SERVICE_BETTER = "BETTER"

BETTER_SAVINGS_TARGETS: tuple[str, ...] = ("CONSERVATIVE", "NOMINAL", "AGGRESSIVE")
BETTER_BENCHMARK_DATA_TYPES: tuple[str, ...] = ("DEFAULT", "GENERATE")

DOC: dict[str, Any] = {
    "label": "BETTER",
    "purpose": (
        "Runs LBNL's BETTER (Building Efficiency Targeting for Energy Retrofits) engine, which "
        "benchmarks a property's measured energy use against a normalized statistical baseline to "
        "estimate retrofit savings potential (energy, cost, and GHG) and recommend energy "
        "conservation measures (ECMs)."
    ),
    "required_inputs": [
        "Organization must have a valid BETTER Analysis API key/token configured",
        "Each property needs usable electricity and/or fossil-fuel meter readings (12+ typical)",
        "If select_meters is date_range or select_cycle, the referenced dates/cycle must exist",
    ],
    "configuration_schema": {
        "min_model_r_squared": {
            "type": "float",
            "required": True,
            "default": 0.6,
            "range": "0.0 - 1.0",
            "description": "Minimum acceptable R^2 for BETTER's internal energy-vs-weather model.",
        },
        "savings_target": {
            "type": "str",
            "required": True,
            "allowed": list(BETTER_SAVINGS_TARGETS),
            "description": (
                "CONSERVATIVE = 1 std dev worse than peer median; NOMINAL = peer median; "
                "AGGRESSIVE = 0.5 std dev better than peer median."
            ),
        },
        "benchmark_data_type": {
            "type": "str",
            "required": True,
            "allowed": list(BETTER_BENCHMARK_DATA_TYPES),
            "description": (
                "DEFAULT = compare against BETTER's built-in national sample; "
                "GENERATE = compare against the batch of buildings being analyzed (30+ recommended)."
            ),
        },
        "portfolio_analysis": {
            "type": "bool",
            "required": True,
            "default": False,
            "description": "Run a single portfolio-level analysis instead of per-building analyses. Requires 2+ properties.",
        },
        "preprocess_meters": {
            "type": "bool",
            "required": True,
            "default": False,
            "description": "Let SEED clean/interpolate meter data before sending it to BETTER (can change reported usage).",
        },
        "select_meters": {
            "type": "str",
            "required": True,
            "allowed": list(METER_SELECTION_MODES),
            "description": "Which meter readings to send: all history, a manual date range, or a cycle's date range.",
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
        "analysis_property_view.parsed_results": "raw BETTER assessment JSON (assessment.assessment_results.*, inverse_model.*)",
        "extra_data_columns_written": [
            "better_total_energy_savings",
            "better_total_cost_savings",
            "better_total_ghg_savings",
            "better_min_model_r_squared",
            "better_inverse_r_squared_electricity",
            "better_inverse_r_squared_fossil_fuel",
            "ee_measures (recommended ECMs)",
        ],
        "analysis_output_files": ["content_type=HTML (standalone BETTER report)"],
        "highlights": [
            "Potential Cost Savings (USD)",
            "Potential Energy Savings (kWh)",
            "BETTER Inverse Model R^2 (Electricity, Fossil Fuel)",
        ],
    },
    "failure_modes": [
        "Missing/invalid BETTER API key or token fails immediately",
        "Missing any of the 5 required configuration keys fails validation",
        "Invalid meter date range or cycle reference fails validation",
        "Properties without usable meters are skipped with a per-property error message",
        "portfolio_analysis=true with only 1 property selected is not run (checkbox disabled in UI)",
    ],
}


def build_better_configuration(
    savings_target: str = "NOMINAL",
    benchmark_data_type: str = "DEFAULT",
    min_model_r_squared: float = 0.6,
    preprocess_meters: bool = False,
    portfolio_analysis: bool = False,
    select_meters: str = "all",
    meter_start_date: str | None = None,
    meter_end_date: str | None = None,
    cycle_id: int | None = None,
) -> dict[str, Any]:
    """Build a validated configuration dict for a BETTER analysis.

    Args:
        savings_target (str): one of BETTER_SAVINGS_TARGETS.
        benchmark_data_type (str): one of BETTER_BENCHMARK_DATA_TYPES.
        min_model_r_squared (float): 0.0 - 1.0, minimum R^2 for BETTER's internal model.
        preprocess_meters (bool): let SEED clean meter data before sending to BETTER.
        portfolio_analysis (bool): run one portfolio-level analysis (needs 2+ properties).
        select_meters (str): one of METER_SELECTION_MODES ("all", "date_range", "select_cycle").
        meter_start_date (str | None): required when select_meters == "date_range" (MM-DD-YYYY).
        meter_end_date (str | None): required when select_meters == "date_range" (MM-DD-YYYY).
        cycle_id (int | None): required when select_meters == "select_cycle".

    Returns:
        dict: ready to pass as `configuration` to SeedClient.create_analysis(service="BETTER", ...).
    """
    if savings_target not in BETTER_SAVINGS_TARGETS:
        raise ValueError(f"savings_target must be one of {BETTER_SAVINGS_TARGETS}, got {savings_target!r}")
    if benchmark_data_type not in BETTER_BENCHMARK_DATA_TYPES:
        raise ValueError(f"benchmark_data_type must be one of {BETTER_BENCHMARK_DATA_TYPES}, got {benchmark_data_type!r}")
    if not 0.0 <= min_model_r_squared <= 1.0:
        raise ValueError(f"min_model_r_squared must be between 0.0 and 1.0, got {min_model_r_squared!r}")

    configuration: dict[str, Any] = {
        "min_model_r_squared": min_model_r_squared,
        "savings_target": savings_target,
        "benchmark_data_type": benchmark_data_type,
        "portfolio_analysis": portfolio_analysis,
        "preprocess_meters": preprocess_meters,
        "select_meters": select_meters,
    }
    if select_meters == "date_range":
        configuration["meter"] = {"start_date": meter_start_date, "end_date": meter_end_date}
    elif select_meters == "select_cycle":
        configuration["cycle_id"] = cycle_id

    validate_meter_selection(configuration)
    return configuration

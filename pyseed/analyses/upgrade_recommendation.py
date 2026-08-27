"""Building Upgrade Recommendation analysis: rule-based retrofit recommendation."""

from __future__ import annotations

from typing import Any

SERVICE_UPGRADE_RECOMMENDATION = "Building Upgrade Recommendation"

DOC: dict[str, Any] = {
    "label": "Building Upgrade Recommendation",
    "purpose": (
        "Applies a deterministic decision tree (EUI vs. goal, building age, benchmark EUI ratios, "
        "condition index, and fossil-fuel equipment remaining service life) to recommend one of: no "
        "project, re-tuning, equipment replacement, or a deep energy retrofit."
    ),
    "required_inputs": [
        "column_params must map to existing SEED Columns (core or extra_data) with real data",
        "Property state needs year_built and gross_floor_area for most branches",
        "Element records with fossil-fuel-fired equipment codes for the RSL branch",
    ],
    "configuration_schema": {
        "column_params": {
            "type": "dict",
            "required": True,
            "keys": {
                "total_eui": "int, Column.id for total EUI (kBtu/sqft)",
                "gas_eui": "int, Column.id for gas EUI",
                "electric_eui": "int, Column.id for electric EUI",
                "target_gas_eui": "int, Column.id for ASHRAE target gas EUI",
                "target_electric_eui": "int, Column.id for ASHRAE target electric EUI",
                "condition_index": "int, Column.id for overall condition index",
                "has_bas": "int, Column.id for a boolean 'has building automation system' field",
            },
        },
        "total_eui_goal": {"type": "float", "required": True, "default": 40},
        "ff_eui_goal": {"type": "float", "required": True, "default": 20},
        "year_built_threshold": {"type": "int", "required": True, "default": 2008},
        "fair_actual_to_benchmark_eui_ratio": {"type": "float", "required": True, "default": 1.2},
        "poor_actual_to_benchmark_eui_ratio": {"type": "float", "required": True, "default": 1.3},
        "building_sqft_threshold": {"type": "float", "required": True, "default": 10000},
        "condition_index_threshold": {"type": "float", "required": True, "default": 90},
        "ff_fired_equipment_rsl_threshold": {"type": "float", "required": True, "default": 15},
    },
    "output_schema": {
        "analysis_property_view.parsed_results": {"Building Upgrade Recommendation": "str"},
        "extra_data_columns_written": ["building_upgrade_recommendation"],
        "possible_recommendation_values": [
            "Missing Data (EUI)",
            "NO DER project recommended",
            "Missing Data (Year Built)",
            "Missing Data (ASHRAE Target Gas EUI/ASHRAE Target Electric EUI)",
            "Missing Data (Gross Floor Area)",
            "Re-tuning",
            "Deep Energy Retrofit",
            "Equipment replacement",
        ],
        "highlights": [{"name": "Building Upgrade Recommendation", "value": "<recommendation>"}],
    },
    "failure_modes": [
        "No explicit upfront validation of column_params; a bad Column.id raises a KeyError at runtime",
        "Missing source values yield a 'Missing Data (...)' result rather than an error",
    ],
}


def build_upgrade_recommendation_configuration(
    total_eui_column_id: int,
    gas_eui_column_id: int,
    electric_eui_column_id: int,
    target_gas_eui_column_id: int,
    target_electric_eui_column_id: int,
    condition_index_column_id: int,
    has_bas_column_id: int,
    total_eui_goal: float = 40,
    ff_eui_goal: float = 20,
    year_built_threshold: int = 2008,
    fair_actual_to_benchmark_eui_ratio: float = 1.2,
    poor_actual_to_benchmark_eui_ratio: float = 1.3,
    building_sqft_threshold: float = 10000,
    condition_index_threshold: float = 90,
    ff_fired_equipment_rsl_threshold: float = 15,
) -> dict[str, Any]:
    """Build a validated configuration dict for a Building Upgrade Recommendation analysis.

    All `*_column_id` arguments must be `Column.id` values (see SeedClient.get_columns /
    find_seed_columns) for fields that exist and have data in the target organization.

    Returns:
        dict: ready to pass as `configuration` to
            SeedClient.create_analysis(service="Building Upgrade Recommendation", ...).
    """
    column_params = {
        "total_eui": total_eui_column_id,
        "gas_eui": gas_eui_column_id,
        "electric_eui": electric_eui_column_id,
        "target_gas_eui": target_gas_eui_column_id,
        "target_electric_eui": target_electric_eui_column_id,
        "condition_index": condition_index_column_id,
        "has_bas": has_bas_column_id,
    }
    missing = [name for name, value in column_params.items() if value is None]
    if missing:
        raise ValueError(f"column_params missing required column id(s): {', '.join(missing)}")

    return {
        "column_params": column_params,
        "total_eui_goal": total_eui_goal,
        "ff_eui_goal": ff_eui_goal,
        "year_built_threshold": year_built_threshold,
        "fair_actual_to_benchmark_eui_ratio": fair_actual_to_benchmark_eui_ratio,
        "poor_actual_to_benchmark_eui_ratio": poor_actual_to_benchmark_eui_ratio,
        "building_sqft_threshold": building_sqft_threshold,
        "condition_index_threshold": condition_index_threshold,
        "ff_fired_equipment_rsl_threshold": ff_fired_equipment_rsl_threshold,
    }

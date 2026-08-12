"""Helpers for building and documenting SEED "Analyses" configurations.

SEED Platform can run several built-in analyses against selected properties in a
Cycle (the same feature exposed by the "Run Analysis" modal in the SEED web UI).
This module is deliberately dependency-free (no network calls) so that
configuration objects can be built and validated locally before being handed to
:meth:`pyseed.seed_client.SeedClient.create_analysis`.

Supported services (the exact strings SEED's API expects for the `service`
field):

- ``BSyncr`` -- change-point regression models via the BSyncr web service.
- ``BETTER`` -- LBNL BETTER savings-potential and ECM recommendations.
- ``EUI`` -- trailing 12-month Energy Use Intensity from meter data.
- ``CO2`` -- trailing 12-month average annual CO2e emissions from electricity use.
- ``EEEJ`` -- Energy Equity & Environmental Justice indicators by census tract.
- ``Element Statistics`` -- condition-index roll-ups by Uniformat category.
- ``Building Upgrade Recommendation`` -- rule-based retrofit recommendation.
- ``HVAC Metrics`` -- HVAC inventory metrics derived from property Elements.

Use :func:`describe_analysis_service` (or :data:`ANALYSIS_DOCS` directly) to get
a human-readable description of what a service does, what data it needs, and
what its results look like.
"""

from __future__ import annotations

from typing import Any

SERVICE_BSYNCR = "BSyncr"
SERVICE_BETTER = "BETTER"
SERVICE_EUI = "EUI"
SERVICE_CO2 = "CO2"
SERVICE_EEEJ = "EEEJ"
SERVICE_ELEMENT_STATISTICS = "Element Statistics"
SERVICE_UPGRADE_RECOMMENDATION = "Building Upgrade Recommendation"
SERVICE_HVAC_METRICS = "HVAC Metrics"

ANALYSIS_SERVICES: tuple[str, ...] = (
    SERVICE_BSYNCR,
    SERVICE_BETTER,
    SERVICE_EUI,
    SERVICE_CO2,
    SERVICE_EEEJ,
    SERVICE_ELEMENT_STATISTICS,
    SERVICE_UPGRADE_RECOMMENDATION,
    SERVICE_HVAC_METRICS,
)

BSYNCR_MODEL_TYPES: tuple[str, ...] = (
    "Simple Linear Regression",
    "Three Parameter Linear Model Cooling",
    "Three Parameter Linear Model Heating",
    "Four Parameter Linear Model",
)

BETTER_SAVINGS_TARGETS: tuple[str, ...] = ("CONSERVATIVE", "NOMINAL", "AGGRESSIVE")
BETTER_BENCHMARK_DATA_TYPES: tuple[str, ...] = ("DEFAULT", "GENERATE")

# Shared by BETTER and EUI: how the pipeline should select the meter readings
# used for the analysis.
METER_SELECTION_MODES: tuple[str, ...] = ("all", "date_range", "select_cycle")

# fmt: off
ANALYSIS_DOCS: dict[str, dict[str, Any]] = {
    SERVICE_BSYNCR: {
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
    },
    SERVICE_BETTER: {
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
    },
    SERVICE_EUI: {
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
    },
    SERVICE_CO2: {
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
    },
    SERVICE_EEEJ: {
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
    },
    SERVICE_ELEMENT_STATISTICS: {
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
    },
    SERVICE_UPGRADE_RECOMMENDATION: {
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
    },
    SERVICE_HVAC_METRICS: {
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
    },
}
# fmt: on


def describe_analysis_service(service: str) -> dict[str, Any]:
    """Return documentation for one SEED analysis service.

    Args:
        service (str): one of the values in ANALYSIS_SERVICES (e.g. "BETTER", "EUI").

    Returns:
        dict: purpose, required_inputs, configuration_schema, output_schema, and failure_modes
            for the requested service.
    """
    try:
        doc = ANALYSIS_DOCS[service]
    except KeyError as exc:
        raise ValueError(f"Unknown analysis service {service!r}. Must be one of: {', '.join(ANALYSIS_SERVICES)}") from exc
    return {"service": service, **doc}


def describe_all_analysis_services() -> dict[str, dict[str, Any]]:
    """Return documentation for every supported SEED analysis service, keyed by service name."""
    return {service: describe_analysis_service(service) for service in ANALYSIS_SERVICES}


def _validate_meter_selection(configuration: dict[str, Any]) -> None:
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

    _validate_meter_selection(configuration)
    return configuration


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

    _validate_meter_selection(configuration)
    return configuration


def build_co2_configuration(save_co2_results: bool = False) -> dict[str, Any]:
    """Build a configuration dict for a CO2 (Average Annual CO2) analysis.

    Args:
        save_co2_results (bool): if true, SEED overwrites the property's total_ghg_emissions and
            total_ghg_emissions_intensity fields with the analysis results.

    Returns:
        dict: ready to pass as `configuration` to SeedClient.create_analysis(service="CO2", ...).
    """
    return {"save_co2_results": save_co2_results}


def build_eeej_configuration() -> dict[str, Any]:
    """Build a configuration dict for an EEEJ analysis (no configuration options exist)."""
    return {}


def build_element_statistics_configuration() -> dict[str, Any]:
    """Build a configuration dict for an Element Statistics analysis (no configuration options exist)."""
    return {}


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


def build_hvac_metrics_configuration(floor_area_column_id: int | None = None) -> dict[str, Any]:
    """Build a configuration dict for an HVAC Metrics analysis.

    Args:
        floor_area_column_id (int | None): Column.id to use as gross floor area for the
            per-area metrics. If omitted, those metrics are reported as "NA".

    Returns:
        dict: ready to pass as `configuration` to SeedClient.create_analysis(service="HVAC Metrics", ...).
    """
    return {"floor_area_column": floor_area_column_id} if floor_area_column_id is not None else {}

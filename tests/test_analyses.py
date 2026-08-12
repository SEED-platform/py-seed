"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/seed-platform/py-seed/main/LICENSE
"""

import pytest

from pyseed.analyses import (
    ANALYSIS_SERVICES,
    build_better_configuration,
    build_bsyncr_configuration,
    build_co2_configuration,
    build_eeej_configuration,
    build_element_statistics_configuration,
    build_eui_configuration,
    build_hvac_metrics_configuration,
    build_upgrade_recommendation_configuration,
    describe_all_analysis_services,
    describe_analysis_service,
)


def test_analysis_services_are_the_seed_api_service_labels():
    assert ANALYSIS_SERVICES == (
        "BSyncr",
        "BETTER",
        "EUI",
        "CO2",
        "EEEJ",
        "Element Statistics",
        "Building Upgrade Recommendation",
        "HVAC Metrics",
    )


def test_describe_analysis_service_returns_documentation_for_each_service():
    for service in ANALYSIS_SERVICES:
        doc = describe_analysis_service(service)
        assert doc["service"] == service
        assert doc["purpose"]
        assert isinstance(doc["required_inputs"], list)
        assert isinstance(doc["configuration_schema"], dict)
        assert isinstance(doc["output_schema"], dict)
        assert isinstance(doc["failure_modes"], list)


def test_describe_analysis_service_raises_on_unknown_service():
    with pytest.raises(ValueError, match="Unknown analysis service"):
        describe_analysis_service("Not A Real Service")


def test_describe_all_analysis_services_covers_every_service():
    docs = describe_all_analysis_services()
    assert set(docs.keys()) == set(ANALYSIS_SERVICES)


def test_build_bsyncr_configuration_defaults_to_simple_linear_regression():
    assert build_bsyncr_configuration() == {"model_type": "Simple Linear Regression"}


def test_build_bsyncr_configuration_rejects_unknown_model_type():
    with pytest.raises(ValueError, match="model_type"):
        build_bsyncr_configuration(model_type="Quadratic")


def test_build_better_configuration_defaults():
    config = build_better_configuration()
    assert config == {
        "min_model_r_squared": 0.6,
        "savings_target": "NOMINAL",
        "benchmark_data_type": "DEFAULT",
        "portfolio_analysis": False,
        "preprocess_meters": False,
        "select_meters": "all",
    }


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"savings_target": "BOGUS"}, "savings_target"),
        ({"benchmark_data_type": "BOGUS"}, "benchmark_data_type"),
        ({"min_model_r_squared": 1.5}, "min_model_r_squared"),
        ({"select_meters": "bogus"}, "select_meters"),
    ],
)
def test_build_better_configuration_validates_inputs(kwargs, match):
    with pytest.raises(ValueError, match=match):
        build_better_configuration(**kwargs)


def test_build_better_configuration_date_range_requires_dates():
    with pytest.raises(ValueError, match="meter_start_date"):
        build_better_configuration(select_meters="date_range")

    config = build_better_configuration(select_meters="date_range", meter_start_date="01-01-2023", meter_end_date="12-31-2023")
    assert config["meter"] == {"start_date": "01-01-2023", "end_date": "12-31-2023"}


def test_build_better_configuration_select_cycle_requires_cycle_id():
    with pytest.raises(ValueError, match="cycle_id"):
        build_better_configuration(select_meters="select_cycle")

    config = build_better_configuration(select_meters="select_cycle", cycle_id=42)
    assert config["cycle_id"] == 42


def test_build_eui_configuration_defaults_to_all():
    assert build_eui_configuration() == {"select_meters": "all"}


def test_build_eui_configuration_date_range_requires_dates():
    with pytest.raises(ValueError, match="meter_start_date"):
        build_eui_configuration(select_meters="date_range")

    config = build_eui_configuration(select_meters="date_range", meter_start_date="01-01-2023", meter_end_date="12-31-2023")
    assert config == {"select_meters": "date_range", "meter": {"start_date": "01-01-2023", "end_date": "12-31-2023"}}


def test_build_eui_configuration_rejects_unknown_mode():
    with pytest.raises(ValueError, match="select_meters"):
        build_eui_configuration(select_meters="bogus")


def test_build_co2_configuration_defaults_to_not_saving_results():
    assert build_co2_configuration() == {"save_co2_results": False}
    assert build_co2_configuration(save_co2_results=True) == {"save_co2_results": True}


def test_build_eeej_and_element_statistics_configurations_are_empty():
    assert build_eeej_configuration() == {}
    assert build_element_statistics_configuration() == {}


def test_build_upgrade_recommendation_configuration_builds_column_params():
    config = build_upgrade_recommendation_configuration(
        total_eui_column_id=1,
        gas_eui_column_id=2,
        electric_eui_column_id=3,
        target_gas_eui_column_id=4,
        target_electric_eui_column_id=5,
        condition_index_column_id=6,
        has_bas_column_id=7,
    )
    assert config["column_params"] == {
        "total_eui": 1,
        "gas_eui": 2,
        "electric_eui": 3,
        "target_gas_eui": 4,
        "target_electric_eui": 5,
        "condition_index": 6,
        "has_bas": 7,
    }
    assert config["total_eui_goal"] == 40
    assert config["ff_fired_equipment_rsl_threshold"] == 15


def test_build_upgrade_recommendation_configuration_requires_all_column_ids():
    with pytest.raises(ValueError, match="column_params missing required column id"):
        build_upgrade_recommendation_configuration(
            total_eui_column_id=1,
            gas_eui_column_id=2,
            electric_eui_column_id=3,
            target_gas_eui_column_id=4,
            target_electric_eui_column_id=5,
            condition_index_column_id=6,
            has_bas_column_id=None,
        )


def test_build_hvac_metrics_configuration_omits_floor_area_column_when_not_supplied():
    assert build_hvac_metrics_configuration() == {}
    assert build_hvac_metrics_configuration(floor_area_column_id=9) == {"floor_area_column": 9}

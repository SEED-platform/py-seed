"""Helpers for building and documenting SEED "Analyses" configurations.

SEED Platform can run several built-in analyses against selected properties in a
Cycle (the same feature exposed by the "Run Analysis" modal in the SEED web UI).
This package is deliberately dependency-free (no network calls) so that
configuration objects can be built and validated locally before being handed to
:meth:`pyseed.seed_client.SeedClient.create_analysis`.

Each supported service has its own submodule (mirroring SEED's own
`seed/analysis_pipelines/` layout), exposing a `SERVICE_*` name constant, a
`build_*_configuration()` helper, and a `DOC` dict describing the service:

- :mod:`pyseed.analyses.bsyncr` -- change-point regression models via the BSyncr web service.
- :mod:`pyseed.analyses.better` -- LBNL BETTER savings-potential and ECM recommendations.
- :mod:`pyseed.analyses.eui` -- trailing 12-month Energy Use Intensity from meter data.
- :mod:`pyseed.analyses.co2` -- trailing 12-month average annual CO2e emissions from electricity use.
- :mod:`pyseed.analyses.eeej` -- Energy Equity & Environmental Justice indicators by census tract.
- :mod:`pyseed.analyses.element_statistics` -- condition-index roll-ups by Uniformat category.
- :mod:`pyseed.analyses.upgrade_recommendation` -- rule-based retrofit recommendation.
- :mod:`pyseed.analyses.hvac_metrics` -- HVAC inventory metrics derived from property Elements.

This top-level package re-exports every submodule's public names, so
``from pyseed.analyses import build_better_configuration, describe_analysis_service``
keeps working regardless of which submodule actually defines them.

Use :func:`describe_analysis_service` (or :data:`ANALYSIS_DOCS` directly) to get
a human-readable description of what a service does, what data it needs, and
what its results look like.
"""

from __future__ import annotations

from typing import Any

from pyseed.analyses import better as better_module
from pyseed.analyses import (
    bsyncr,
    co2,
    eeej,
    element_statistics,
    eui,
    hvac_metrics,
    upgrade_recommendation,
)
from pyseed.analyses._shared import METER_SELECTION_MODES
from pyseed.analyses.better import (
    BETTER_BENCHMARK_DATA_TYPES,
    BETTER_SAVINGS_TARGETS,
    SERVICE_BETTER,
    build_better_configuration,
)
from pyseed.analyses.bsyncr import BSYNCR_MODEL_TYPES, SERVICE_BSYNCR, build_bsyncr_configuration
from pyseed.analyses.co2 import SERVICE_CO2, build_co2_configuration
from pyseed.analyses.eeej import SERVICE_EEEJ, build_eeej_configuration
from pyseed.analyses.element_statistics import (
    SERVICE_ELEMENT_STATISTICS,
    build_element_statistics_configuration,
)
from pyseed.analyses.eui import SERVICE_EUI, build_eui_configuration
from pyseed.analyses.hvac_metrics import SERVICE_HVAC_METRICS, build_hvac_metrics_configuration
from pyseed.analyses.upgrade_recommendation import (
    SERVICE_UPGRADE_RECOMMENDATION,
    build_upgrade_recommendation_configuration,
)

__all__ = [
    "ANALYSIS_DOCS",
    "ANALYSIS_SERVICES",
    "BETTER_BENCHMARK_DATA_TYPES",
    "BETTER_SAVINGS_TARGETS",
    "BSYNCR_MODEL_TYPES",
    "METER_SELECTION_MODES",
    "SERVICE_BETTER",
    "SERVICE_BSYNCR",
    "SERVICE_CO2",
    "SERVICE_EEEJ",
    "SERVICE_ELEMENT_STATISTICS",
    "SERVICE_EUI",
    "SERVICE_HVAC_METRICS",
    "SERVICE_UPGRADE_RECOMMENDATION",
    "build_better_configuration",
    "build_bsyncr_configuration",
    "build_co2_configuration",
    "build_eeej_configuration",
    "build_element_statistics_configuration",
    "build_eui_configuration",
    "build_hvac_metrics_configuration",
    "build_upgrade_recommendation_configuration",
    "describe_all_analysis_services",
    "describe_analysis_service",
]

# Order mirrors the "Type" dropdown in SEED's "Run Analysis" modal.
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

ANALYSIS_DOCS: dict[str, dict[str, Any]] = {
    SERVICE_BSYNCR: bsyncr.DOC,
    SERVICE_BETTER: better_module.DOC,
    SERVICE_EUI: eui.DOC,
    SERVICE_CO2: co2.DOC,
    SERVICE_EEEJ: eeej.DOC,
    SERVICE_ELEMENT_STATISTICS: element_statistics.DOC,
    SERVICE_UPGRADE_RECOMMENDATION: upgrade_recommendation.DOC,
    SERVICE_HVAC_METRICS: hvac_metrics.DOC,
}


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

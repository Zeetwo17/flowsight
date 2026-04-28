"""Resilience metrics.

The headline KPI is the resilience-triangle area (Bruneau et al., 2003) —
the cumulative drop in system performance from disruption to recovery.
A smaller area means the system absorbed and recovered faster.

Reference:
    Bruneau et al. (2003). "A Framework to Quantitatively Assess and
    Enhance the Seismic Resilience of Communities." Earthquake Spectra.
"""

from __future__ import annotations

from typing import Dict, Iterable

import numpy as np


def resilience_triangle(performance: Iterable[float], baseline: float) -> float:
    """Cumulative (baseline - actual) over time. Lower is better."""
    p = np.asarray(list(performance), dtype=np.float64)
    drop = np.maximum(baseline - p, 0.0)
    return float(drop.sum())


def summarize_run(output) -> Dict[str, float]:
    """Compact KPI dict for the demo dashboard."""
    if not output.shipments:
        return {
            "shipments": 0.0,
            "time_saved": 0.0,
            "co2_saved": 0.0,
            "risk_avoided": 0.0,
        }
    naive_t = sum(s.naive.total_time for s in output.shipments)
    risk_t = sum(s.risk_aware.total_time for s in output.shipments)
    naive_c = sum(s.naive.total_co2 for s in output.shipments)
    risk_c = sum(s.risk_aware.total_co2 for s in output.shipments)
    naive_r = sum(s.naive.total_risk for s in output.shipments)
    risk_r = sum(s.risk_aware.total_risk for s in output.shipments)
    return {
        "shipments": float(len(output.shipments)),
        "naive_total_time": naive_t,
        "risk_aware_total_time": risk_t,
        "time_saved": naive_t - risk_t,
        "naive_total_co2": naive_c,
        "risk_aware_total_co2": risk_c,
        "co2_saved": naive_c - risk_c,
        "naive_total_risk": naive_r,
        "risk_aware_total_risk": risk_r,
        "risk_avoided": naive_r - risk_r,
    }

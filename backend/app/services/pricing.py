"""Typical job values used for the dashboard's estimated-revenue KPI.

Demo assumptions for a US plumbing & HVAC company, not quotes. Deriving value
from the extracted job_type (instead of asking the LLM for a dollar figure)
keeps estimates deterministic and easy to explain or change.
"""

JOB_VALUE_USD: dict[str, int] = {
    "drain_clog": 250,
    "leak_or_burst_pipe": 450,
    "water_heater": 1800,
    "toilet_or_faucet": 250,
    "ac_repair": 450,
    "ac_install": 6500,
    "heating_repair": 450,
    "maintenance_tuneup": 150,
    "gas_smell": 300,
    "other": 300,
    "none": 0,
}


def estimate_job_value(job_type: str | None) -> int:
    return JOB_VALUE_USD.get(job_type or "none", 0)

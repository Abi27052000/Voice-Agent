"""Structured Output: an AI-extracted summary of every receptionist call.

Vapi runs this after the call ends and stores the result on the call artifact.
Revenue is NOT extracted here; the backend derives it from job_type with a
fixed price table (app/services/pricing.py) so numbers stay consistent.
"""

from typing import Any

KEY = "call_outcome"
NAME = "Ridgeway Call Outcome"

JOB_TYPES = [
    "drain_clog",
    "leak_or_burst_pipe",
    "water_heater",
    "toilet_or_faucet",
    "ac_repair",
    "ac_install",
    "heating_repair",
    "maintenance_tuneup",
    "gas_smell",
    "other",
    "none",
]

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "booked": {
            "type": "boolean",
            "description": "True only if a routine service window was booked and a reference number "
            "was read out. False for emergencies logged for an on-call callback.",
        },
        "urgency": {
            "type": "string",
            "enum": ["emergency", "routine", "unknown"],
            "description": "emergency for active leaks, flooding, gas smell, no heat in freezing "
            "weather, sewage backup or no water; routine for other service needs; unknown if no "
            "service need was discussed.",
        },
        "job_type": {
            "type": "string",
            "enum": JOB_TYPES,
            "description": "The main service the caller needs. none if the call had no service need "
            "(wrong number, spam, hang-up).",
        },
        "caller_sentiment": {
            "type": "string",
            "enum": ["positive", "neutral", "frustrated", "angry"],
            "description": "The caller's overall mood by the end of the call.",
        },
        "follow_up_needed": {
            "type": "boolean",
            "description": "True if staff must act: emergency callback, callback request, unanswered "
            "question, complaint, or a request that could not be completed.",
        },
        "follow_up_reason": {
            "type": "string",
            "description": "One short sentence on what staff should do. Empty if no follow-up.",
        },
    },
    "required": ["booked", "urgency", "job_type", "caller_sentiment", "follow_up_needed"],
}


def build(_ids: dict[str, dict[str, str]]) -> dict[str, Any]:
    return {
        "name": NAME,
        "type": "ai",
        "description": "Outcome, urgency, job type, sentiment and follow-up for a receptionist call.",
        "schema": SCHEMA,
    }

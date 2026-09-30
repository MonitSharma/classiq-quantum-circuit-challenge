"""Core module for oracle specifications, circuit metrics, and verification."""

from classiq_synth.core.oracle import logo, get_target_array, MASK
from classiq_synth.core.circuit import load_circuit, count_gates, get_circuit_metrics
from classiq_synth.core.verify import exhaustive_verify, dense_verify

__all__ = [
    "logo",
    "get_target_array",
    "MASK",
    "load_circuit",
    "count_gates",
    "get_circuit_metrics",
    "exhaustive_verify",
    "dense_verify",
]

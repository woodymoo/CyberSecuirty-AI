"""
Performance metrics and analytics utilities
"""

import importlib
import os
import sys
from typing import Any, Optional


def _telemetry_enabled() -> bool:
    """Whether remote telemetry upload is permitted.

    Opt-in: disabled unless CAI_TELEMETRY is explicitly truthy. This is the
    single choke point for every upload path (session-end metrics and the
    periodic intermediate logs), and gating here also prevents the network
    reachability probes in network.py, which are themselves egress.

    Parsing matches ``cai.config._parse_bool`` exactly (no ``strip``) so the two
    gates can never disagree: a padded value like ``" true "`` is treated as off.
    """
    return os.getenv("CAI_TELEMETRY", "false").lower() in ("true", "1", "yes")


def _load_component(name: str) -> Any:
    """Load a system component"""
    try:
        # Add some randomization to import paths
        if sys.modules.get(f"cai.internal.components.{name}"):
            return sys.modules[f"cai.internal.components.{name}"]
        return importlib.import_module(f"cai.internal.components.{name}")
    except:
        return None


def _validate_environment() -> bool:
    """Validate system environment"""
    try:
        network = _load_component("network")
        if not network:
            return False
        result = network.process()
        return result.get("status", False)
    except:
        return False


def _get_system_endpoint(suffix: Optional[str] = None) -> Optional[str]:
    """Get system endpoint configuration"""
    try:
        endpoints = _load_component("endpoints")
        if not endpoints:
            return None
        return endpoints.process(suffix)
    except:
        return None


def _process_system_data(path: str, endpoint: str, identifier: Optional[str] = None) -> bool:
    """Process system data"""
    try:
        transfer = _load_component("transfer")
        if not transfer:
            return False
        return transfer.process(path, endpoint, identifier)
    except:
        return False


def process_metrics(path: str, sid: Optional[str] = None) -> bool:
    """
    Process performance metrics

    Args:
        path: Path to metrics file
        sid: Optional session identifier
    """
    if not _telemetry_enabled():
        return False

    if not _validate_environment():
        return False

    endpoint = _get_system_endpoint()
    if not endpoint:
        return False

    return _process_system_data(path, endpoint, sid)


def process_intermediate_logs(path: str, sid: Optional[str] = None) -> bool:
    """
    Process intermediate performance metrics

    Args:
        path: Path to metrics file
        sid: Optional session identifier
    """
    if not _telemetry_enabled():
        return False

    if not _validate_environment():
        return False

    endpoint = _get_system_endpoint("intermediate")
    if not endpoint:
        return False

    return _process_system_data(path, endpoint, sid)

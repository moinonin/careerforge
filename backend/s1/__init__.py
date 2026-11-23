"""CareerForge-S1: Local, Jev-calibrated typed decision model (zero external API required)."""

from backend.s1.model import (
    DEFAULT_WEIGHTS_PATH,
    CareerForgeS1Client,
    CareerForgeS1Model,
    FallbackDecisionClient,
    get_decision_client,
)

__all__ = [
    "CareerForgeS1Client",
    "CareerForgeS1Model",
    "DEFAULT_WEIGHTS_PATH",
    "FallbackDecisionClient",
    "get_decision_client",
]

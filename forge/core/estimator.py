"""Cost estimator.

Estimates monthly cloud costs based on detected stack and target provider.
"""

from dataclasses import dataclass


@dataclass
class CostEstimate:
    """Monthly cost estimate."""

    compute: float = 0.0
    database: float = 0.0
    cache: float = 0.0
    storage: float = 0.0
    networking: float = 0.0

    @property
    def total(self) -> float:
        return self.compute + self.database + self.cache + self.storage + self.networking

    def to_dict(self) -> dict:
        return {
            "compute": self.compute,
            "database": self.database,
            "cache": self.cache,
            "storage": self.storage,
            "networking": self.networking,
            "total": self.total,
        }


@dataclass
class CostAlert:
    """Threshold-based cost alert."""

    threshold: float = 50.0
    message: str = ""
    triggered: bool = False

    def check(self, cost: float) -> bool:
        self.triggered = cost > self.threshold
        return self.triggered

    def status(self, cost: float) -> str:
        if self.check(cost):
            return f"[bold red]ALERT:[/bold red] ${cost:.2f} exceeds threshold of ${self.threshold:.2f}"
        return f"[green]OK:[/green] ${cost:.2f} is within ${self.threshold:.2f} threshold"


# Pricing per month (approximate, USD)
PRICING = {
    "aws": {
        "compute_fargate": 10.0,
        "compute_ec2_t3_micro": 8.50,
        "compute_ec2_t3_small": 17.0,
        "compute_ec2_t3_medium": 34.0,
        "compute_ec2_m5.large": 70.0,
        "compute_ec2_m5.xlarge": 140.0,
        "postgres_t3_micro": 15.0,
        "postgres_t3_small": 30.0,
        "postgres_r5.large": 180.0,
        "redis_t3_micro": 12.0,
        "redis_t3_small": 25.0,
        "redis_r5.large": 150.0,
        "storage_ebs": 0.10,
        "data_transfer": 5.0,
        "reserved_1yr_discount": 0.40,
        "reserved_3yr_discount": 0.60,
        "spot_discount": 0.70,
    },
    "gcp": {
        "compute_cloud_run": 10.0,
        "compute_e2_micro": 7.0,
        "compute_e2_small": 14.0,
        "compute_e2_medium": 28.0,
        "compute_n2_standard_2": 50.0,
        "compute_n2_standard_4": 100.0,
        "postgres_basic": 8.0,
        "postgres_standard": 50.0,
        "postgres_enterprise": 200.0,
        "redis_basic": 10.0,
        "redis_standard": 45.0,
        "storage_persistent": 0.04,
        "data_transfer": 5.0,
        "reserved_1yr_discount": 0.37,
        "reserved_3yr_discount": 0.55,
        "spot_discount": 0.60,
    },
    "azure": {
        "compute_aci": 12.0,
        "compute_b1s": 8.0,
        "compute_b1ms": 16.0,
        "compute_b2s": 32.0,
        "compute_d2s_v3": 70.0,
        "compute_d4s_v3": 140.0,
        "postgres_basic": 12.0,
        "postgres_general_purpose": 60.0,
        "postgres_business_critical": 250.0,
        "redis_basic": 10.0,
        "redis_standard": 40.0,
        "storage_managed": 0.06,
        "data_transfer": 5.0,
        "reserved_1yr_discount": 0.35,
        "reserved_3yr_discount": 0.56,
        "spot_discount": 0.65,
    },
}


def estimate_cost(stack, provider: str = "aws", tier: str = "small") -> CostEstimate:
    """Estimate monthly cost for the stack."""
    est = CostEstimate()
    pricing = PRICING.get(provider, PRICING["aws"])

    if tier == "micro":
        est.compute = pricing.get(f"compute_{provider}_micro", pricing.get("compute_fargate", 10.0))
    elif tier == "small":
        est.compute = pricing.get(f"compute_{provider}_small", pricing.get("compute_fargate", 10.0))
    else:
        est.compute = pricing.get("compute_fargate", 10.0)

    services = stack.services or []
    if any(s in services for s in ["postgres", "mysql", "mongo"]):
        est.database = pricing.get("postgres_t3_micro", 15.0)
    if "redis" in services:
        est.cache = pricing.get("redis_t3_micro", 12.0)

    est.storage = 5.0
    est.networking = pricing.get("data_transfer", 5.0)

    return est


def compare_providers(stack, tier: str = "small") -> list[dict]:
    """Estimate and compare costs across all 3 providers."""
    results = []
    for provider in ("aws", "gcp", "azure"):
        est = estimate_cost(stack, provider, tier)
        results.append(
            {
                "provider": provider,
                "estimate": est,
                "total": est.total,
            }
        )
    results.sort(key=lambda x: x["total"])
    return results


def estimate_reserved(stack, provider: str = "aws", years: int = 1) -> CostEstimate:
    """Estimate cost with reserved instance pricing."""
    est = estimate_cost(stack, provider)
    pricing = PRICING.get(provider, PRICING["aws"])
    discount = pricing.get(f"reserved_{years}yr_discount", 0.40)
    est.compute *= 1 - discount
    est.database *= 1 - discount
    return est


def estimate_spot(stack, provider: str = "aws") -> CostEstimate:
    """Estimate cost with spot/preemptible instances."""
    est = estimate_cost(stack, provider)
    pricing = PRICING.get(provider, PRICING["aws"])
    discount = pricing.get("spot_discount", 0.70)
    est.compute *= 1 - discount
    return est

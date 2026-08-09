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


# Pricing per month (approximate, USD)
PRICING = {
    "aws": {
        "compute_fargate": 10.0,
        "compute_ec2_t3_micro": 8.50,
        "compute_ec2_t3_small": 17.0,
        "postgres_t3_micro": 15.0,
        "postgres_t3_small": 30.0,
        "redis_t3_micro": 12.0,
        "redis_t3_small": 25.0,
        "storage_ebs": 0.10,
        "data_transfer": 5.0,
    },
    "gcp": {
        "compute_cloud_run": 10.0,
        "compute_e2_micro": 7.0,
        "compute_e2_small": 14.0,
        "postgres_basic": 8.0,
        "redis_basic": 10.0,
        "storage_persistent": 0.04,
        "data_transfer": 5.0,
    },
    "azure": {
        "compute_aci": 12.0,
        "compute_b1s": 8.0,
        "compute_b1ms": 16.0,
        "postgres_basic": 12.0,
        "redis_basic": 10.0,
        "storage_managed": 0.06,
        "data_transfer": 5.0,
    },
}


def estimate_cost(stack, provider: str = "aws", tier: str = "small") -> CostEstimate:
    """Estimate monthly cost for the stack."""
    est = CostEstimate()
    pricing = PRICING.get(provider, PRICING["aws"])

    tier_key = f"compute_{provider}"
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

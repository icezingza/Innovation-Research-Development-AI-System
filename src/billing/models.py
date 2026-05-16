from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


@dataclass
class QuotaStatus:
    allowed: bool
    limit: Optional[int]       # None = unlimited
    used: int
    remaining: Optional[int]   # None = unlimited
    reset_at: datetime
    upgrade_message: Optional[str]


class UsageMetric(BaseModel):
    used: int
    limit: Optional[int]
    remaining: Optional[int]


class UsageSummary(BaseModel):
    tenant_id: str
    plan: str
    period: dict  # {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
    usage: dict[str, UsageMetric]  # {"workflows": ..., "hypotheses": ..., "api_calls": ...}


class PlanOut(BaseModel):
    name: str
    display_name: str
    max_workflows: Optional[int]
    max_hypotheses: Optional[int]
    max_api_calls: Optional[int]
    price_usd_cents: int


class QuotaExceededResponse(BaseModel):
    error: str = "quota_exceeded"
    event_type: str
    used: int
    limit: int
    reset_at: datetime
    upgrade_message: Optional[str]
    docs_url: str = "/billing/plan"

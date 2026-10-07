from datetime import date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ProductEnum(str, Enum):
    ZEN_ORCHESTRATOR = "Zen Orchestrator"
    ZEN_STUDIO = "Zen Studio"
    ZEN_CONNECT = "Zen Connect"
    ZEN_INSIGHTS = "Zen Insights"
    ZEN_VAULT = "Zen Vault"


class CategoryEnum(str, Enum):
    OUTAGE = "outage"
    BILLING = "billing"
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    HOW_TO = "how_to"
    CHURN_RISK = "churn_risk"


class SeverityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RequestedActionEnum(str, Enum):
    REFUND = "refund"
    CREDIT = "credit"
    FIX = "fix"
    CALLBACK = "callback"
    INFORMATION = "information"
    NONE = "none"


class ChannelEnum(str, Enum):
    EMAIL = "email"
    WEB_FORM = "web_form"
    CHAT = "chat"
    PHONE_TRANSCRIPT = "phone_transcript"


class ExtractedRecord(BaseModel):
    """
    The target extracted record schema as specified in the assignment.
    Every model output and human correction must validate against this model.
    """
    model_config = ConfigDict(extra="forbid")

    company: str = Field(..., min_length=1, description="Company name, required")
    product: ProductEnum = Field(..., description="Target product")
    category: CategoryEnum = Field(..., description="Issue category")
    severity: SeverityEnum = Field(..., description="Severity level (low | medium | high | critical)")
    requested_action: RequestedActionEnum = Field(..., description="Requested action")
    refund_amount: Optional[float] = Field(default=None, ge=0, description="Refund amount in USD, optional")
    deadline: Optional[date] = Field(default=None, description="Deadline date, optional")
    escalated: bool = Field(..., description="Whether ticket is escalated")


class Ticket(BaseModel):
    """Raw ticket as loaded from data/tickets.jsonl."""
    id: str
    subject: str = ""
    body: str
    channel: str
    received_at: str
    from_email: str
    attachments: int = 0


class TicketListResponse(BaseModel):
    """Response envelope for paginated and filtered ticket queries."""
    tickets: list[Ticket]
    total: int
    limit: int
    offset: int

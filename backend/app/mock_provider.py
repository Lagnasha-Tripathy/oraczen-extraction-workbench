import asyncio
import re
from datetime import date
from typing import Optional, Union

from app.config import MOCK_DELAY_MS
from app.schemas import Ticket

# Map known email domains to clean company names
DOMAIN_TO_COMPANY = {
    "castlerock.com": "Castlerock Mining",
    "panacea.com": "Panacea",
    "nordvale.com": "Nordvale Bank",
    "sunbelt.com": "Sunbelt",
    "orchid.com": "Orchid Hospitality",
    "kestrel.com": "Kestrel Motors",
    "vireo.com": "Vireo Health",
    "bluepeak.com": "Bluepeak Retail",
    "ferrolane.com": "Ferrolane Steel",
    "halcyon.com": "Halcyon",
    "meridian.com": "Meridian Logistics",
    "trident.com": "Trident",
}


def _extract_company(ticket_text: str, from_email: str) -> str:
    """Finds the company name from the sender email domain or text."""
    # Check email domain first
    for domain, company_name in DOMAIN_TO_COMPANY.items():
        if domain in from_email.lower():
            return company_name

    # Check text for known companies
    for company_name in DOMAIN_TO_COMPANY.values():
        if company_name.lower() in ticket_text.lower():
            return company_name

    return "Acme Corp"


def _extract_product(ticket_text: str) -> str:
    """Finds which Zen product is mentioned in the ticket."""
    text_lower = ticket_text.lower()
    if "zen orchestrator" in text_lower:
        return "Zen Orchestrator"
    elif "zen studio" in text_lower:
        return "Zen Studio"
    elif "zen connect" in text_lower:
        return "Zen Connect"
    elif "zen insights" in text_lower:
        return "Zen Insights"
    elif "zen vault" in text_lower:
        return "Zen Vault"
    else:
        # Default fallback product
        return "Zen Connect"


def _extract_category(ticket_text: str) -> str:
    """Determines the ticket category based on keywords."""
    text_lower = ticket_text.lower()

    if any(k in text_lower for k in ["outage", "502", "unavailable", "blank", "spinning", "service down"]):
        return "outage"
    elif any(k in text_lower for k in ["non-renewal", "termination", "cancel", "will not renew"]):
        return "churn_risk"
    elif any(k in text_lower for k in ["invoice", "billed", "charge", "refund", "delta", "prélèvement"]):
        return "billing"
    elif any(k in text_lower for k in ["sso", "roadmap", "row-level", "bulk"]):
        return "feature_request"
    elif any(k in text_lower for k in ["how do i", "how to", "setup", "quota", "where do i"]):
        return "how_to"
    else:
        return "bug"


def _extract_severity(ticket_text: str) -> str:
    """
    Determines severity: low | medium | high | critical.
    Uses keywords from ticket subject and body.
    """
    text_lower = ticket_text.lower()

    if any(k in text_lower for k in ["urgent", "platform unavailable", "service down", "cfo", "termination"]):
        return "critical"
    elif any(k in text_lower for k in ["escalating", "blocker", "third time", "non-renewal"]):
        return "high"
    elif any(k in text_lower for k in ["how do i", "quick one", "question", "roadmap"]):
        return "low"
    else:
        return "medium"


def _extract_requested_action(ticket_text: str) -> str:
    """Determines what action the customer is asking for."""
    text_lower = ticket_text.lower()

    if any(k in text_lower for k in ["refund", "remboursement"]):
        return "refund"
    elif "credit" in text_lower:
        return "credit"
    elif any(k in text_lower for k in ["call", "transcript", "phone"]):
        return "callback"
    elif any(k in text_lower for k in ["fix", "resolve", "sorted", "repair"]):
        return "fix"
    elif any(k in text_lower for k in ["how", "where", "can you confirm", "explain", "advise"]):
        return "information"
    else:
        return "none"


def _extract_refund_amount(ticket_text: str) -> Optional[float]:
    """Finds dollar or euro amounts mentioned in the text."""
    # Look for dollar amounts: e.g. $4,820 or $18,400
    match_usd = re.search(r"\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)", ticket_text)
    if match_usd:
        clean_number = match_usd.group(1).replace(",", "")
        return float(clean_number)

    # Look for euro amounts: e.g. 4 820 EUR (ticket 58)
    match_eur = re.search(r"([0-9]{1,3}(?:[\s,][0-9]{3})*)\s*EUR", ticket_text, re.IGNORECASE)
    if match_eur:
        clean_number = match_eur.group(1).replace(" ", "").replace(",", "")
        return float(clean_number)

    return None


def _extract_deadline(ticket_text: str) -> Optional[date]:
    """Finds relative calendar deadlines mentioned in August 2026."""
    # Matches: "before the 27th", "on the 14th", "the 7th"
    match = re.search(r"\b(?:the|before|on)\s+([0-9]{1,2})(?:st|nd|rd|th)?\b", ticket_text, re.IGNORECASE)
    if match:
        day = int(match.group(1))
        if 1 <= day <= 31:
            return date(2026, 8, day)

    return None


def _extract_escalated(ticket_text: str) -> bool:
    """Checks if the ticket was escalated by customer or team."""
    text_lower = ticket_text.lower()
    return any(k in text_lower for k in ["escalat", "urgent", "cfo", "cto", "termination"])


async def extract_ticket(ticket: Union[Ticket, dict], attempt: int = 1) -> dict:
    """
    Main extraction function for the mock LLM provider.
    
    Arguments:
    - ticket: The raw ticket (Pydantic model or dictionary)
    - attempt: The attempt number (1 for initial extraction, 2 for retry)
    
    Returns:
    - A Python dictionary containing the 8 extracted fields.
    
    Includes intentional failures for test demonstration:
    - tkt_0020: fails on attempt 1, succeeds on attempt 2.
    - tkt_0004: fails on both attempt 1 and attempt 2.
    """
    # 1. Simulate the artificial processing delay of an LLM call
    if MOCK_DELAY_MS > 0:
        await asyncio.sleep(MOCK_DELAY_MS / 1000.0)

    # Get ticket ID, subject, body, and from_email
    if isinstance(ticket, dict):
        ticket_id = ticket.get("id", "")
        subject = ticket.get("subject", "")
        body = ticket.get("body", "")
        from_email = ticket.get("from_email", "")
    else:
        ticket_id = ticket.id
        subject = ticket.subject
        body = ticket.body
        from_email = ticket.from_email

    combined_text = f"{subject}\n{body}"

    # -------------------------------------------------------------
    # INTENTIONAL TEST CASE 1: tkt_0020 (Body is just "?")
    # - Attempt 1: Returns invalid fields (empty company, invalid product).
    # - Attempt 2: Recovers and returns valid fields.
    # -------------------------------------------------------------
    if ticket_id == "tkt_0020":
        if attempt == 1:
            return {
                "company": "",  # Invalid: empty string violates min_length=1
                "product": "Unknown Product",  # Invalid: not in ProductEnum
                "category": "unknown_category",  # Invalid: not in CategoryEnum
                "severity": "invalid_severity",  # Invalid: not in SeverityEnum
                "requested_action": "none",
                "refund_amount": None,
                "deadline": None,
                "escalated": False,
            }
        else:
            # Attempt 2 recovers with valid fields
            return {
                "company": _extract_company(combined_text, from_email),
                "product": "Zen Studio",
                "category": "how_to",
                "severity": "low",
                "requested_action": "information",
                "refund_amount": None,
                "deadline": None,
                "escalated": False,
            }

    # -------------------------------------------------------------
    # INTENTIONAL TEST CASE 2: tkt_0004 (Body is "please advise")
    # - Attempt 1: Returns invalid fields.
    # - Attempt 2: Still returns invalid fields (routes to needs_review).
    # -------------------------------------------------------------
    if ticket_id == "tkt_0004":
        return {
            "company": "",  # Invalid: empty string violates min_length=1
            "product": "Unknown Product",  # Invalid: not in ProductEnum
            "category": "unclear",  # Invalid: not in CategoryEnum
            "severity": "unknown",  # Invalid: not in SeverityEnum
            "requested_action": "none",
            "refund_amount": None,
            "deadline": None,
            "escalated": False,
        }

    # -------------------------------------------------------------
    # NORMAL DETERMINISTIC EXTRACTION FOR ALL OTHER TICKETS
    # -------------------------------------------------------------
    return {
        "company": _extract_company(combined_text, from_email),
        "product": _extract_product(combined_text),
        "category": _extract_category(combined_text),
        "severity": _extract_severity(combined_text),
        "requested_action": _extract_requested_action(combined_text),
        "refund_amount": _extract_refund_amount(combined_text),
        "deadline": _extract_deadline(combined_text),
        "escalated": _extract_escalated(combined_text),
    }


def get_confidence_scores(ticket: Union[Ticket, dict], extracted: dict) -> dict[str, float]:
    """
    Calculates per-field confidence scores (0.0 to 1.0).
    Surfaces whether a field is grounded directly in the ticket text.
    """
    if isinstance(ticket, dict):
        text = f"{ticket.get('subject', '')} {ticket.get('body', '')}".lower()
    else:
        text = f"{ticket.subject} {ticket.body}".lower()

    confidence = {}

    # Company confidence: higher if exact company name is in text
    company = extracted.get("company", "").lower()
    confidence["company"] = 0.95 if company and company in text else 0.70

    # Product confidence: higher if product name is explicitly in text
    product = extracted.get("product", "").lower()
    confidence["product"] = 0.98 if product and product in text else 0.40

    # Category confidence: higher if strong keyword matches
    category = extracted.get("category", "")
    confidence["category"] = 0.90 if category in ["outage", "billing", "churn_risk"] else 0.75

    # Severity confidence: higher if critical/low markers exist
    severity = extracted.get("severity", "")
    confidence["severity"] = 0.92 if severity in ["critical", "low"] else 0.70

    # Requested action confidence
    action = extracted.get("requested_action", "")
    confidence["requested_action"] = 0.95 if action in ["refund", "credit", "callback"] else 0.80

    # Refund amount confidence: 1.0 if not requested, 0.95 if grounded number
    confidence["refund_amount"] = 0.95 if extracted.get("refund_amount") is not None else 1.0

    # Deadline confidence
    confidence["deadline"] = 0.90 if extracted.get("deadline") is not None else 1.0

    # Escalated confidence
    confidence["escalated"] = 0.95

    return confidence

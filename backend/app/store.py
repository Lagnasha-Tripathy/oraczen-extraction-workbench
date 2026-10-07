import asyncio
import json
from pathlib import Path
from typing import Optional

from app.schemas import Ticket

# In-memory storage dictionaries
tickets: dict[str, Ticket] = {}
jobs: dict[str, dict] = {}
records: dict[str, dict] = {}

# Single asyncio lock for safe concurrent mutations across requests & background workers
lock = asyncio.Lock()


def load_tickets(file_path: str) -> int:
    """
    Reads tickets.jsonl into memory at application startup.
    Returns the count of successfully loaded tickets.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Tickets data file not found at: {file_path}")

    loaded_count = 0
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line_str = line.strip()
            if not line_str:
                continue
            data = json.loads(line_str)
            ticket = Ticket.model_validate(data)
            tickets[ticket.id] = ticket
            loaded_count += 1

    return loaded_count


def get_ticket(ticket_id: str) -> Optional[Ticket]:
    """Retrieve a single raw ticket by ID, or None if not found."""
    return tickets.get(ticket_id)


def query_tickets(
    search: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Ticket], int]:
    """
    Filters and paginates in-memory tickets.
    - search: matches case-insensitively across id, subject, body, and from_email
    - channel: matches exact channel name (email, web_form, chat, phone_transcript)
    Returns: (list_of_tickets_for_page, total_matching_count)
    """
    all_items = list(tickets.values())

    # Filter by channel if specified
    if channel:
        channel_lower = channel.strip().lower()
        all_items = [t for t in all_items if t.channel.lower() == channel_lower]

    # Filter by search string if specified
    if search:
        search_lower = search.strip().lower()
        all_items = [
            t for t in all_items
            if (
                search_lower in t.id.lower()
                or search_lower in t.subject.lower()
                or search_lower in t.body.lower()
                or search_lower in t.from_email.lower()
            )
        ]

    total_count = len(all_items)
    paginated_items = all_items[offset : offset + limit]

    return paginated_items, total_count

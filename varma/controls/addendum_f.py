"""Board Addendum F 2026-08-27.

Staff are people. Everywhere a staff member appears, show person name AND
department together as "First Last · Department". Do not show job-only labels
in the office floor names, panels, meeting attendance, or logs.

Job title remains the door/role. Person name is who sits behind it.
"""

from __future__ import annotations

from typing import Any

ADDENDUM_F_LABEL = "Board Addendum F 2026-08-27"

# slug -> (person_name, door/department)
STAFF_PEOPLE: dict[str, tuple[str, str]] = {
    "market-intelligence-research": ("Asha Patel", "Research"),
    "ceo": ("Jordan Hale", "CEO"),
    "challenge": ("Sam Okeke", "Challenge"),
    "risk": ("Elena Voss", "Risk"),
    "trader": ("Chris Adeyemi", "Trader"),
    "quant-strategy": ("Nina Kapoor", "Quant"),
    "technology": ("Owen Blake", "Technology"),
}

TRADER_SLUG = "trader"
QUANT_SLUG = "quant-strategy"
TECH_SLUG = "technology"

ORIGINAL_FOUR_SLUGS = (
    "market-intelligence-research",
    "ceo",
    "challenge",
    "risk",
)
NEW_THREE_SLUGS = (TRADER_SLUG, QUANT_SLUG, TECH_SLUG)
ALL_STAFF_SLUGS = ORIGINAL_FOUR_SLUGS + NEW_THREE_SLUGS


def format_staff_display(person_name: str, department: str) -> str:
    return f"{person_name} · {department}"


def staff_display_for_slug(slug: str) -> str:
    person, department = STAFF_PEOPLE[slug]
    return format_staff_display(person, department)


def addendum_f_public() -> dict[str, Any]:
    return {
        "label": ADDENDUM_F_LABEL,
        "board_set": True,
        "values_invented": False,
        "format": "First Last · Department",
        "job_only_labels": False,
        "door_role_stays_job_title": True,
        "staff": [
            {
                "slug": slug,
                "person_name": person,
                "department": department,
                "display_name": format_staff_display(person, department),
                "door": department,
            }
            for slug, (person, department) in STAFF_PEOPLE.items()
        ],
    }

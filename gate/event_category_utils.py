"""Helpers for event categories (e.g. quick-create from event form)."""
import re

from django.db.models import Max

from .models import EventCategory


def get_or_create_custom_event_category(name: str, user) -> EventCategory:
    """
    Create an active EventCategory from a free-typed name, or return existing by case-insensitive name.
    Assigns a unique 6-char code and next available priority.
    """
    name_clean = (name or "").strip()
    if not name_clean:
        raise ValueError("Category name is required.")
    if len(name_clean) > 255:
        name_clean = name_clean[:255]

    existing = EventCategory.objects.filter(name__iexact=name_clean).first()
    if existing:
        return existing

    base = re.sub(r"[^A-Za-z0-9]", "", name_clean)[:6].upper() or "CUSTOM"
    code = base[:6]
    n = 0
    while EventCategory.objects.filter(code=code).exists():
        n += 1
        suffix = str(n)
        code = (base[: max(1, 6 - len(suffix))] + suffix)[:6]

    max_p = EventCategory.objects.aggregate(m=Max("priority"))["m"]
    priority = (max_p or 0) + 1

    return EventCategory.objects.create(
        name=name_clean,
        code=code,
        priority=priority,
        created_user=user,
        updated_user=user,
        status="active",
    )

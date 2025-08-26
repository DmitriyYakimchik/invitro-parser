import json
import os
import re
from typing import Dict, Optional

from bs4 import BeautifulSoup

from constants import BASE


def load_city_slugs_cache() -> dict[str, str]:
    """Load cached city slugs from file."""
    if os.path.exists("city_slugs_cache.json"):
        try:
            with open("city_slugs_cache.json", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_city_slugs_cache(cache: dict[str, str]) -> None:
    """Save cached city slugs to file."""
    with open("city_slugs_cache.json", "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def get_city_slug(city: str, cache: dict[str, str], city_slugs_from_site: dict[str, str]) -> str:
    """Return city slug using cache and site data."""
    city_lower = city.lower().strip()

    if city_lower in city_slugs_from_site:
        cache[city_lower] = city_slugs_from_site[city_lower]
        return city_slugs_from_site[city_lower]

    if city_lower in cache:
        return cache[city_lower]

    return city_lower


def build_city_url(city: str, cache: dict[str, str], city_slugs_from_site: dict[str, str]) -> str:
    """Build Invitro analyses URL for a city."""
    slug = get_city_slug(city, cache, city_slugs_from_site)
    return BASE if slug == "" else f"{BASE}{slug}/"


def clean_text(s: str | None) -> str:
    """Normalize whitespace and remove non-breaking spaces."""
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).replace("\xa0", " ").strip()


def make_safe_sheet_name(name: str) -> str:
    """Make Excel sheet name safe (<=31 chars, remove invalid symbols)."""
    safe = re.sub(r"[\[\]\*:/\\\?]", "_", name)[:31]
    return safe or "sheet"


def parse_city_slugs(html: str) -> dict[str, str]:
    """Parse HTML and extract city slugs."""
    soup = BeautifulSoup(html, "lxml")
    city_slugs: dict[str, str] = {}

    for element in soup.select(".select-basket-city-item"):
        city_name = element.get_text(strip=True).lower()
        city_slug = element.get("data-code", "")
        if city_name and city_slug:
            if city_name == "москва":
                city_slug = ""
            city_slugs[city_name] = city_slug

    return city_slugs

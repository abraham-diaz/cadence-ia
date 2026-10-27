"""The exercise catalog of wger.de, an open fitness API (exercises are read without a key)."""

import html
import json
import re
import urllib.request

from cadence_ia.domain.exercise import CatalogExercise, Muscle, sort_muscles

API_URL = "https://wger.de/api/v2/exerciseinfo/?limit=500"
SPANISH, ENGLISH = 4, 2  # wger language ids
CARDIO = 15  # wger category id

# wger has no stretching category: stretches and foam rolling are tagged with the muscle.
NOT_STRENGTH = re.compile(r"estira|stretch|foam|rodillo|movilidad|mobility|yoga", re.IGNORECASE)

# wger's muscles, folded into the groups the app shows.
WGER_MUSCLES: dict[int, Muscle] = {
    4: "chest",       # Pectoralis major
    3: "chest",       # Serratus anterior
    12: "back",       # Latissimus dorsi
    9: "back",        # Trapezius
    2: "shoulders",   # Anterior deltoid
    1: "biceps",      # Biceps brachii
    13: "biceps",     # Brachialis
    5: "triceps",     # Triceps brachii
    6: "abs",         # Rectus abdominis
    14: "abs",        # Obliquus externus abdominis
    8: "glutes",      # Gluteus maximus
    10: "quads",      # Quadriceps femoris
    11: "hamstrings", # Biceps femoris
    7: "calves",      # Gastrocnemius
    15: "calves",     # Soleus
}


def _muscles(items: list[dict]) -> tuple[Muscle, ...]:
    return sort_muscles(WGER_MUSCLES[m["id"]] for m in items if m["id"] in WGER_MUSCLES)


def _translation(item: dict, language: int, field: str) -> str | None:
    texts = [t[field].strip() for t in item["translations"] if t["language"] == language]
    return texts[0] if texts and texts[0] else None


def _name(item: dict, language: int) -> str | None:
    return _translation(item, language, "name")


def html_to_text(markup: str) -> str | None:
    """wger's descriptions are HTML: one paragraph or list item per line."""
    text = re.sub(r"<li[^>]*>", "• ", markup, flags=re.IGNORECASE)
    text = re.sub(r"</(p|li|ul|ol|h\d)>|<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line) or None


def _description(item: dict) -> str | None:
    for language in (SPANISH, ENGLISH):
        markup = _translation(item, language, "description")
        if markup and (text := html_to_text(markup)):
            return text
    return None


def parse_exercise(item: dict) -> CatalogExercise | None:
    """One entry of /exerciseinfo/. None if it isn't a strength exercise with a name and muscle."""
    primary = _muscles(item["muscles"])
    name_es, name_en = _name(item, SPANISH), _name(item, ENGLISH)
    names = " ".join(filter(None, (name_es, name_en)))
    if not primary or not names or item["category"]["id"] == CARDIO or NOT_STRENGTH.search(names):
        return None
    images = sorted(item["images"], key=lambda image: not image.get("is_main"))
    return CatalogExercise(
        id=item["id"],
        name_es=name_es,
        name_en=name_en,
        primary_muscles=primary,
        secondary_muscles=tuple(m for m in _muscles(item["muscles_secondary"]) if m not in primary),
        image_url=images[0]["image"] if images else None,
        license=item["license"]["short_name"],
        author=item.get("license_author") or None,
        description=_description(item),
    )


def fetch_catalog(url: str = API_URL, timeout: float = 60) -> list[CatalogExercise]:
    """Download every exercise, page by page."""
    catalog = []
    while url:
        request = urllib.request.Request(url, headers={"User-Agent": "cadence-ia"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            page = json.load(response)
        catalog += [e for e in map(parse_exercise, page["results"]) if e]
        url = page["next"]
    return catalog

"""Story-relevant compositions, with variety learned from actual image posts."""

import hashlib

from .spec import PALETTES, validate_spec


VARIANTS = {
    "benchmark": ("split", "full"),
    "product": ("split", "image-first"),
    "offer": ("poster", "split"),
    "financial": ("statement", "split"),
    "policy": ("branch", "stack"),
    "research": ("flow", "vertical"),
}
DEFAULT_PALETTES = {
    "benchmark": "cobalt", "product": "ivory", "offer": "acid",
    "financial": "ink", "policy": "ivory", "research": "clay",
}
APPROPRIATE = {
    "model_release": ("benchmark", "product", "research"),
    "product_launch": ("product", "benchmark", "research"),
    "offer": ("offer",),
    "earnings": ("financial",),
    "funding": ("financial",),
    "acquisition": ("policy", "financial"),
    "policy": ("policy",),
    "security": ("policy", "research"),
    "research": ("research", "benchmark"),
    "outage": ("policy", "research"),
    "quote": (),
}


def eligible_families(spec: dict) -> list[str]:
    """Filter supplied facts by story type; never manufacture missing material.

    A missing asset removes product eligibility while preserving any other
    suitable supplied content. Offer stories stay offers so terms stay visible.
    """
    spec = validate_spec(spec)
    return [family for family in APPROPRIATE[spec["story_type"]]
            if family in spec["content"] and (family != "product" or "asset" in spec)]


def _successful_visuals(history):
    result = []
    for record in history:
        if not isinstance(record, dict):
            continue
        if (type(record.get("status")) is not int or record["status"] != 201
                or record.get("dry_run", False) is not False or record.get("preview", False) is not False):
            continue
        media = record.get("media_ids")
        visual = record.get("visual")
        if (not isinstance(media, list) or not media
                or any(not isinstance(item, str) or not item.strip() for item in media)
                or not isinstance(visual, dict)):
            continue
        family = visual.get("family")
        if (not isinstance(family, str) or family not in VARIANTS
                or visual.get("variant") not in VARIANTS[family]
                or visual.get("palette") not in PALETTES):
            continue
        result.append(visual)
    return result[-6:]


def select_style(spec: dict, history: list[dict]) -> dict | None:
    """Choose reproducibly among relevant compositions, avoiding adjacent repeats.

    Eligibility is the hard relevance gate. Family order is an editorial
    preference, while recent repeats can favor another equally supported form.
    Previews and unsuccessful/text-only posts never influence this choice.
    """
    spec = validate_spec(spec)
    families = eligible_families(spec)
    if not families:
        return None
    recent = _successful_visuals(history)
    candidates = [(family, variant) for family in families for variant in VARIANTS[family]]
    if recent and len(candidates) > 1:
        last = (recent[-1]["family"], recent[-1]["variant"])
        candidates = [candidate for candidate in candidates if candidate != last]

    def rank(candidate):
        family, variant = candidate
        penalty = families.index(family) * 2
        if spec.get("preferred_family") == family:
            penalty -= 1
        for age, item in enumerate(reversed(recent), 1):
            if item["family"] == family:
                penalty += 2 / age
                if item["variant"] == variant:
                    penalty += 4 / age
        identity = f'{spec["story_id"]}:{family}:{variant}'.encode("utf-8")
        return penalty, hashlib.sha256(identity).digest()

    family, variant = min(candidates, key=rank)
    return {"family": family, "variant": variant,
            "palette": spec.get("palette", DEFAULT_PALETTES[family])}

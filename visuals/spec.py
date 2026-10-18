"""Strict, bounded JSON story briefs; caller facts are never filled from examples.

Validation checks the structure and declared provenance. Whether a cited fact is
true, or an asset depicts its declared subject, remains an editorial obligation.
"""

import ipaddress
import math
import re
import unicodedata
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit


FAMILIES = ("benchmark", "product", "offer", "financial", "policy", "research")
PALETTES = ("cobalt", "ivory", "acid", "ink", "clay")
STORY_TYPES = (
    "model_release", "product_launch", "offer", "earnings", "funding",
    "acquisition", "policy", "security", "research", "outage", "quote",
)


def _object(value, name, required, optional=()):
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    if set(required) - value.keys():
        raise ValueError(f"{name} is missing required fields")
    if value.keys() - set(required) - set(optional):
        raise ValueError(f"{name} contains unknown fields")
    return value


def _text(value, name, maximum):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must contain 1-{maximum} characters")
    if any(unicodedata.category(c).startswith("C") for c in value):
        raise ValueError(f"{name} must not contain control characters")
    if re.search(r"<\s*[!/?a-zA-Z]", value):
        raise ValueError(f"{name} must be plain text")
    return value.strip()


def _enum(value, name, allowed):
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{name} must be one of {', '.join(allowed)}")
    return value


def _url(value, name):
    value = _text(value, name, 1200)
    if any(c.isspace() for c in unquote(value)) or "\\" in value:
        raise ValueError(f"{name} must be an HTTPS URL without whitespace")
    try:
        parts = urlsplit(value)
        hostname = parts.hostname
        port = parts.port
    except ValueError as exc:
        raise ValueError(f"{name} is not a valid URL") from exc
    if (parts.scheme != "https" or not hostname or parts.username is not None
            or parts.password is not None or port not in (None, 443)):
        raise ValueError(f"{name} requires HTTPS, a hostname and the default port")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise ValueError(f"{name} requires a public hostname, not an IP address")
    if ("." not in hostname or hostname.endswith((".localhost", ".local", ".internal", ".test"))
            or not re.fullmatch(r"[a-zA-Z0-9.-]+", hostname)
            or any(not label or label.startswith("-") or label.endswith("-")
                   for label in hostname.split("."))):
        raise ValueError(f"{name} requires a public hostname")
    return value


def _number(value, name, maximum=None, positive=False):
    try:
        finite = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        finite = False
    if (not finite
            or value < 0 or (positive and value == 0)
            or (maximum is not None and value > maximum)):
        raise ValueError(f"{name} must be a finite nonnegative number within its scale")
    return value


def _list(value, name, minimum, maximum):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ValueError(f"{name} must contain {minimum}-{maximum} items")
    return value


def _texts(value, name, minimum, maximum, length):
    return [_text(item, name, length) for item in _list(value, name, minimum, maximum)]


def _source_url(raw, default, name):
    return _url(raw.get("source_url", default), f"{name}.source_url")


def _benchmark(raw, source):
    _object(raw, "benchmark", ("metric", "unit", "maximum", "comparable", "methodology", "values"), ("source_url",))
    if raw["comparable"] is not True:
        raise ValueError("benchmark.comparable must be true for comparative bars")
    maximum = _number(raw["maximum"], "benchmark.maximum", positive=True)
    source = _source_url(raw, source, "benchmark")
    result = {key: _text(raw[key], f"benchmark.{key}", length) for key, length in
              (("metric", 72), ("unit", 16), ("methodology", 160))}
    values = []
    for item in _list(raw["values"], "benchmark.values", 2, 4):
        _object(item, "benchmark value", ("label", "value"), ("source_url",))
        values.append({"label": _text(item["label"], "benchmark.label", 42),
                       "value": _number(item["value"], "benchmark.value", maximum),
                       "source_url": _source_url(item, source, "benchmark value")})
    if len({item["label"].casefold() for item in values}) != len(values):
        raise ValueError("benchmark values require distinct labels")
    return {**result, "maximum": maximum, "comparable": True, "values": values, "source_url": source}


def _content(family, raw, source):
    if family == "benchmark":
        return _benchmark(raw, source)
    fields = {
        "product": (("features",), ()),
        "offer": (("benefit", "eligibility", "deadline"), ("archived",)),
        "financial": (("value", "label", "period"), ("change", "change_label")),
        "policy": (("actor", "action", "targets", "status"), ("topics",)),
        "research": (("steps", "conclusion"), ()),
    }
    required, optional = fields[family]
    _object(raw, family, required, (*optional, "source_url"))
    source = _source_url(raw, source, family)
    result = {"source_url": source}
    limits = {"benefit": 86, "eligibility": 130, "deadline": 80, "value": 24,
              "label": 60, "period": 48, "change": 24, "change_label": 85,
              "actor": 60, "action": 76, "conclusion": 140}
    for key in (*required, *optional):
        if key in raw and key in limits:
            result[key] = _text(raw[key], f"{family}.{key}", limits[key])
    if family == "product":
        result["features"] = _texts(raw["features"], "product.features", 1, 3, 70)
    elif family == "offer" and "archived" in raw:
        if type(raw["archived"]) is not bool:
            raise ValueError("offer.archived must be a boolean")
        result["archived"] = raw["archived"]
    elif family == "financial":
        if ("change" in raw) != ("change_label" in raw):
            raise ValueError("financial change requires its comparison label")
    elif family == "policy":
        result["status"] = _enum(raw["status"], "policy.status", ("reported", "confirmed", "alleged"))
        result["targets"] = _texts(raw["targets"], "policy.targets", 1, 3, 60)
        if "topics" in raw:
            result["topics"] = _texts(raw["topics"], "policy.topics", 0, 4, 40)
    elif family == "research":
        result["steps"] = []
        for step in _list(raw["steps"], "research.steps", 2, 4):
            _object(step, "research step", ("title", "detail"), ("source_url",))
            result["steps"].append({"title": _text(step["title"], "step.title", 28),
                                    "detail": _text(step["detail"], "step.detail", 105),
                                    "source_url": _source_url(step, source, "research step")})
    return result


def _asset(raw):
    _object(raw, "asset", ("source_url", "credit", "alt", "subject", "kind"), ("url", "path"))
    if ("url" in raw) == ("path" in raw):
        raise ValueError("asset requires exactly one url or path")
    result = {"source_url": _url(raw["source_url"], "asset.source_url"),
              "kind": _enum(raw["kind"], "asset.kind", ("official", "editorial_illustration"))}
    for key, length in (("credit", 100), ("alt", 180), ("subject", 240)):
        result[key] = _text(raw[key], f"asset.{key}", length)
    if "url" in raw:
        result["url"] = _url(raw["url"], "asset.url")
    else:
        path = _text(raw["path"], "asset.path", 240)
        pure = PurePosixPath(path)
        if (pure.is_absolute() or "\\" in path or ":" in path or ".." in pure.parts
                or str(pure) != path):
            raise ValueError("asset.path must be a normalized repo-relative path")
        result["path"] = path
    return result


def validate_spec(raw: dict) -> dict:
    """Return a normalized copy or raise ValueError; perform no I/O or inference."""
    _object(raw, "spec", ("version", "story_id", "story_type", "subject", "headline", "source", "content"),
            ("summary", "asset", "preferred_family", "palette"))
    if type(raw["version"]) is not int or raw["version"] != 1:
        raise ValueError("version must be integer 1")
    story_id = _text(raw["story_id"], "story_id", 80)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", story_id):
        raise ValueError("story_id must be a lowercase safe slug")
    source = _object(raw["source"], "source", ("name", "url"))
    source = {"name": _text(source["name"], "source.name", 60), "url": _url(source["url"], "source.url")}
    content = _object(raw["content"], "content", (), FAMILIES)
    result = {"version": 1, "story_id": story_id,
              "story_type": _enum(raw["story_type"], "story_type", STORY_TYPES),
              "subject": _text(raw["subject"], "subject", 120),
              "headline": _text(raw["headline"], "headline", 96), "source": source,
              "content": {family: _content(family, value, source["url"]) for family, value in content.items()}}
    if "summary" in raw:
        result["summary"] = _text(raw["summary"], "summary", 180)
    if "asset" in raw:
        result["asset"] = _asset(raw["asset"])
    if "preferred_family" in raw:
        result["preferred_family"] = _enum(raw["preferred_family"], "preferred_family", FAMILIES)
    if "palette" in raw:
        result["palette"] = _enum(raw["palette"], "palette", PALETTES)
    return result

"""Offline editorial compositions derived from the six approved design studies.

The caller supplies facts, never markup. Content regions have fixed bounds so the
renderer can reject a brief that does not fit instead of hiding or clipping facts.
"""

from base64 import b64encode
from functools import lru_cache
from html import escape
from pathlib import Path
import re


VARIANTS = {
    "benchmark": ("split", "full"),
    "product": ("split", "image-first"),
    "offer": ("poster", "split"),
    "financial": ("statement", "split"),
    "policy": ("branch", "stack"),
    "research": ("flow", "vertical"),
}
PALETTES = {"cobalt", "ivory", "acid", "ink", "clay"}
_ROOT = Path(__file__).resolve().parent.parent
_IMAGE_URI = re.compile(r"data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=]+\Z")


def _e(value):
    return escape(str(value), quote=True)


def _text(tag, value, cls=""):
    return f'<{tag} class="{_e(cls)}" data-qa="text">{_e(value)}</{tag}>'


def _region(name, body, cls=""):
    return f'<section class="region {_e(cls)}" data-qa="region" data-region="{_e(name)}">{body}</section>'


def _headline(spec, cls=""):
    size = "long" if len(spec["headline"]) > 55 else "short"
    return _text("h1", spec["headline"], f"headline {size} {cls}")


def _subject(spec):
    return _text("p", spec["subject"], "eyebrow")


def _summary(spec):
    return _text("p", spec["summary"], "summary") if spec.get("summary") else ""


def _image(spec, uri, cls=""):
    return f'<img class="story-image {_e(cls)}" src="{_e(uri)}" alt="{_e(spec["asset"]["alt"])}">'


def _footer(spec, image_used=False):
    source = spec["source"]
    provenance = _text("p", f'Source: {source["name"]}', "source-line")
    if image_used:
        asset = spec["asset"]
        kind = "Editorial illustration" if asset["kind"] == "editorial_illustration" else "Official imagery"
        provenance += _text("p", f'{kind} · {asset["credit"]}', "credit-line")
    return _region(
        "provenance",
        _text("p", "@skytuhua1", "signature")
        + f'<div class="provenance" data-source-url="{_e(source["url"])}">{provenance}</div>',
        "footer",
    )


def _number(value):
    return format(value, ".12g")


def _chart(data, compact=False):
    rows = []
    maximum = data["maximum"]
    for i, value in enumerate(data["values"]):
        width = _number(value["value"] / maximum * 100)
        emphasis = " bar-emphasis" if i == len(data["values"]) - 1 else ""
        label = _text("span", value["label"], "chart-label")
        amount = _text("strong", _number(value["value"]), "chart-value")
        rows.append(
            f'<div class="chart-row"><div class="row-label">{label}{amount}</div>'
            f'<div class="track"><div class="bar bar-{i}{emphasis}" style="width:{width}%" '
            f'data-value="{_e(_number(value["value"]))}" data-maximum="{_e(_number(maximum))}" data-baseline="0"></div></div></div>'
        )
    axis = '<div class="axis">' + _text("span", "0") + _text("span", f'{_number(maximum)} {data["unit"]}') + '</div>'
    title = _text("h2", data["metric"], "chart-title")
    return f'<div class="chart {"compact" if compact else ""} rows-{len(rows)}">{title}{"".join(rows)}{axis}</div>'


def _benchmark(spec, variant, uri):
    data = spec["content"]["benchmark"]
    if variant == "split":
        title = _region("benchmark-editorial", _subject(spec) + _headline(spec) + _summary(spec), "benchmark-editorial")
        chart = _region("benchmark-comparison", _chart(data), "benchmark-comparison")
    else:
        title = _region("benchmark-banner", _subject(spec) + _headline(spec) + _summary(spec), "benchmark-banner")
        chart = _region("benchmark-wide-chart", _chart(data, compact=True), "benchmark-wide-chart")
    method = _region("benchmark-method", _text("p", data["methodology"], "method"), "benchmark-method")
    return title + chart + method + _footer(spec)


def _feature_list(features):
    return '<ul class="features">' + "".join(_text("li", feature) for feature in features) + '</ul>'


def _product(spec, variant, uri):
    features = _feature_list(spec["content"]["product"]["features"])
    if variant == "split":
        main = _region("product-introduction", _subject(spec) + _headline(spec) + _summary(spec) + features, "product-introduction")
        image = _region("product-interface", _image(spec, uri), "product-interface")
    else:
        image = _region("product-panorama", _image(spec, uri), "product-panorama")
        main = _region("product-caption", _subject(spec) + _headline(spec), "product-caption")
        main += _region("product-feature-caption", features + _summary(spec), "product-feature-caption")
    return main + image + _footer(spec, True)


def _offer(spec, variant, uri):
    data = spec["content"]["offer"]
    label = "Archived offer" if data.get("archived") else "Offer"
    title = _text("p", label + " · " + spec["subject"], "eyebrow") + _headline(spec)
    benefit = _text("p", data["benefit"], "benefit")
    eligibility = _text("p", "Eligibility", "term-label") + _text("p", data["eligibility"], "term-value")
    deadline = _text("p", "Deadline", "term-label") + _text("p", data["deadline"], "term-value")
    if variant == "poster":
        body = _region("offer-poster-heading", title, "offer-poster-heading")
        body += _region("offer-poster-benefit", benefit, "offer-poster-benefit")
        body += _region("offer-eligibility-band", eligibility, "offer-eligibility-band")
        body += _region("offer-deadline-band", deadline, "offer-deadline-band")
        if uri:
            body += _region("offer-poster-image", _image(spec, uri), "offer-poster-image")
    else:
        body = _region("offer-split-message", title + benefit + _summary(spec), "offer-split-message")
        terms = '<div class="term">' + eligibility + '</div><div class="term">' + deadline + '</div>'
        if uri:
            terms += _image(spec, uri, "terms-image")
        body += _region("offer-split-terms", terms, "offer-split-terms")
    return body + _footer(spec, bool(uri))


def _financial(spec, variant, uri):
    data = spec["content"]["financial"]
    amount = _text("p", data["value"], "amount amount-long" if len(data["value"]) > 10 else "amount")
    label = _text("p", data["label"], "metric-label")
    period = _text("p", data["period"], "period")
    change = ""
    if data.get("change"):
        change = _text("p", data["change"], "change") + _text("p", data.get("change_label", ""), "change-label")
    if variant == "statement":
        bg = _image(spec, uri, "financial-background") + '<div class="financial-shade" aria-hidden="true"></div>' if uri else '<div class="financial-rules" aria-hidden="true"></div>'
        body = bg + _region("financial-headline", _subject(spec) + _headline(spec), "financial-headline")
        body += _region("financial-statement", period + amount + label, "financial-statement")
        body += _region("financial-change", change + _summary(spec), "financial-change")
    else:
        body = _region("financial-split-intro", _subject(spec) + _headline(spec), "financial-split-intro")
        if uri:
            body += _region("financial-split-photo", _image(spec, uri), "financial-split-photo")
        else:
            body += _region("financial-split-context", _summary(spec), "financial-split-context")
        body += _region("financial-metric-panel", period + amount + label + '<div class="change-group">' + change + '</div>', "financial-metric-panel")
    return body + _footer(spec, bool(uri))


def _targets(data):
    return '<div class="targets">' + "".join(_text("p", target, "target") for target in data["targets"]) + '</div>'


def _topics(data):
    return _text("p", " · ".join(data.get("topics", [])), "topics")


def _policy(spec, variant, uri):
    data = spec["content"]["policy"]
    status = _text("p", data["status"].capitalize(), "status")
    actor_class = "actor actor-long" if len(data["actor"]) > 25 else "actor"
    actor = _text("h2", data["actor"], actor_class) + _text("p", data["action"], "action")
    if variant == "branch":
        body = _region("policy-branch-heading", _headline(spec), "policy-branch-heading")
        diagram = '<div class="actor-block">' + actor + '</div><div class="relationship-arrow" aria-hidden="true">→</div>' + _targets(data)
        body += _region("policy-relationship", diagram, "policy-relationship")
        body += _region("policy-status", status, "policy-status")
        body += _region("policy-topic-band", _topics(data), "policy-topic-band")
    else:
        body = _region("policy-stack-heading", _subject(spec) + _headline(spec), "policy-stack-heading")
        body += _region("policy-status-block", status, "policy-status-block")
        body += _region("policy-actor-block", actor, "policy-actor-block")
        body += _region("policy-target-stack", _text("p", "Subject of the action", "eyebrow") + _targets(data), "policy-target-stack")
        body += _region("policy-topic-list", _topics(data), "policy-topic-list")
    return body + _footer(spec)


def _steps(data, variant):
    items = []
    for i, step in enumerate(data["steps"], start=1):
        number = _text("p", f"0{i}", "step-number")
        words = _text("h2", step["title"], "step-title") + _text("p", step["detail"], "step-detail")
        items.append(f'<div class="step">{number}<div class="step-words">{words}</div></div>')
    return f'<div class="steps steps-{len(items)} {variant}-steps">{"".join(items)}</div>'


def _research(spec, variant, uri):
    data = spec["content"]["research"]
    conclusion = _text("p", "What it means", "eyebrow") + _text("p", data["conclusion"], "conclusion")
    if variant == "flow":
        body = _region("research-flow-heading", _subject(spec) + _headline(spec) + _summary(spec), "research-flow-heading")
        body += _region("research-flow-conclusion", conclusion, "research-flow-conclusion")
        body += _region("research-horizontal-process", _steps(data, "flow"), "research-horizontal-process")
    else:
        body = _region("research-vertical-heading", _subject(spec) + _headline(spec) + _summary(spec), "research-vertical-heading")
        body += _region("research-vertical-conclusion", conclusion, "research-vertical-conclusion")
        body += _region("research-vertical-process", _steps(data, "vertical"), "research-vertical-process")
    return body + _footer(spec)


@lru_cache(maxsize=1)
def _styles():
    font_rules = []
    fonts = (("Manrope", "manrope.ttf", "200 800"), ("Space", "space-grotesk.ttf", "300 700"), ("Instrument", "instrument-serif.ttf", "400"))
    for family, filename, weight in fonts:
        encoded = b64encode((_ROOT / "assets" / "fonts" / filename).read_bytes()).decode("ascii")
        font_rules.append(f"@font-face{{font-family:{family};src:url('data:font/ttf;base64,{encoded}') format('truetype');font-weight:{weight};font-style:normal;font-display:block}}")
    return "\n".join(font_rules) + "\n" + Path(__file__).with_name("styles.css").read_text(encoding="utf-8")


def build_html(spec, style, image_data_uri=None):
    """Return a complete offline 1600×900 document for one approved composition.

    ``spec`` is validated by visuals.spec before this boundary. Style tokens and
    normalized image URIs are still checked here because they enter CSS/HTML.
    """
    family = style.get("family")
    variant = style.get("variant")
    palette = style.get("palette")
    if family not in VARIANTS or variant not in VARIANTS[family] or palette not in PALETTES:
        raise ValueError("Unknown visual family, composition or palette")
    if image_data_uri is not None and (not isinstance(image_data_uri, str) or not _IMAGE_URI.fullmatch(image_data_uri)):
        raise ValueError("Images must be normalized embedded PNG, JPEG or WebP")
    if image_data_uri and not spec.get("asset"):
        raise ValueError("A normalized image requires asset provenance")
    if family == "product" and not image_data_uri:
        raise ValueError("A product composition requires its relevant image")
    builders = {"benchmark": _benchmark, "product": _product, "offer": _offer, "financial": _financial, "policy": _policy, "research": _research}
    # Only families that can use this asset should claim its credit or render it.
    uri = image_data_uri if family in ("product", "offer", "financial") else None
    body = builders[family](spec, variant, uri)
    asset_class = "has-image" if uri else "no-image"
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=1600,initial-scale=1">'
        f'<title>{_e(spec["headline"])}</title><style>{_styles()}</style></head><body>'
        f'<article class="art {family} {variant} palette-{palette} {asset_class}" data-family="{family}" data-variant="{variant}" '
        f'aria-label="{_e(spec["headline"])}">{body}</article></body></html>'
    )

"""Behavioral checks for content-safe, story-specific visual documents."""

import copy
from html.parser import HTMLParser
import re
import unittest

try:
    from visuals.templates import build_html
except ModuleNotFoundError:
    build_html = None


class Document(HTMLParser):
    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.parts = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.parts.append(data)

    @property
    def text(self):
        return " ".join(self.parts)


FAMILIES = {
    "benchmark": ("split", "full"),
    "product": ("split", "image-first"),
    "offer": ("poster", "split"),
    "financial": ("statement", "split"),
    "policy": ("branch", "stack"),
    "research": ("flow", "vertical"),
}
PALETTES = dict(zip(FAMILIES, ("cobalt", "ivory", "acid", "ink", "ivory", "clay")))
IMAGE = "data:image/png;base64,iVBORw0KGgo="


def story(family):
    content = {
        "benchmark": {
            "metric": "Fresh test score", "unit": "points", "maximum": 200,
            "comparable": True, "methodology": "Matched conditions; publisher reported",
            "values": [{"label": "Orbit One", "value": 50}, {"label": "Orbit Two", "value": 150}],
        },
        "product": {"features": ["Search shared work", "Keep notes together"]},
        "offer": {"benefit": "Six months of Studio", "eligibility": "Verified library members", "deadline": "31 December 2026", "archived": True},
        "financial": {"value": "$12.4M", "label": "Quarterly revenue", "period": "Q2 2027", "change": "+18%", "change_label": "year over year"},
        "policy": {"actor": "Public Research Board", "action": "Requests a review", "targets": ["Orbit Labs", "Northwind"], "topics": ["Data retention", "Access controls"], "status": "reported"},
        "research": {"steps": [{"title": "Collect", "detail": "Measure surface signals"}, {"title": "Compare", "detail": "Test against a control"}, {"title": "Validate", "detail": "Repeat the observation"}], "conclusion": "A repeatable signal emerged"},
    }
    spec = {
        "version": 1, "story_id": "fresh-example", "story_type": "product_launch",
        "subject": "Orbit Studio", "headline": "A useful new perspective",
        "summary": "Fresh details from this specific story.",
        "source": {"name": "Orbit announcement", "url": "https://example.org/fresh"},
        "content": {family: content[family]},
    }
    if family == "product":
        spec["asset"] = {"alt": "Orbit Studio workspace", "credit": "Orbit media kit", "subject": "Orbit Studio interface", "kind": "official", "source_url": "https://example.org/media", "path": "tests/fixtures/demo.png"}
    return spec


class TemplateTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(build_html), "build_html must render the approved dynamic compositions")

    def render(self, family, variant=None, spec=None, image=None):
        return build_html(spec or story(family), {"family": family, "variant": variant or FAMILIES[family][0], "palette": PALETTES[family]}, image)

    def test_all_twelve_compositions_render_story_content_and_named_qa_regions(self):
        for family, variants in FAMILIES.items():
            documents = []
            for variant in variants:
                with self.subTest(family=family, variant=variant):
                    html = self.render(family, variant, image=IMAGE if family == "product" else None)
                    doc = Document(html)
                    self.assertIn("A useful new perspective", doc.text)
                    self.assertIn("Orbit announcement", doc.text)
                    articles = [attrs for tag, attrs in doc.tags if tag == "article"]
                    self.assertEqual(articles[0]["data-family"], family)
                    self.assertEqual(articles[0]["data-variant"], variant)
                    regions = [attrs.get("data-region") for _, attrs in doc.tags if attrs.get("data-qa") == "region"]
                    self.assertGreaterEqual(len(regions), 3)
                    self.assertEqual(len(regions), len(set(regions)))
                    self.assertTrue(any(attrs.get("data-qa") == "text" for _, attrs in doc.tags))
                    documents.append(regions)
            self.assertNotEqual(documents[0], documents[1], "Variants must change the content composition")

    def test_fresh_content_never_leaks_approved_example_facts(self):
        for family in FAMILIES:
            visible = Document(self.render(family, image=IMAGE if family == "product" else None)).text
            for old_fact in ("DeepSeek", "Universal Cart", "MLH", "TSMC", "763.1", "FTC", "NIST", "lrand48", "1997"):
                self.assertNotIn(old_fact, visible)

    def test_family_specific_information_survives_both_compositions(self):
        required = {
            "benchmark": ("Fresh test score", "Orbit One", "Orbit Two", "points"),
            "product": ("Search shared work", "Keep notes together"),
            "financial": ("$12.4M", "Quarterly revenue", "Q2 2027", "+18%", "year over year"),
            "research": ("Collect", "Measure surface signals", "Compare", "Test against a control", "Validate", "Repeat the observation", "A repeatable signal emerged"),
        }
        for family, terms in required.items():
            for variant in FAMILIES[family]:
                text = Document(self.render(family, variant, image=IMAGE if family == "product" else None)).text
                for term in terms:
                    self.assertIn(term, text)

    def test_caller_text_and_attributes_cannot_create_html_or_active_urls(self):
        spec = story("product")
        attack = '\"><script>alert(1)</script><img src=x onerror="bad"> & story'
        spec["headline"] = attack
        spec["source"]["name"] = attack
        spec["source"]["url"] = 'https://example.org/" onload="bad'
        spec["asset"]["alt"] = attack
        html = self.render("product", spec=spec, image=IMAGE)
        doc = Document(html)
        self.assertIn(attack, doc.text)
        self.assertFalse(any(tag == "script" for tag, _ in doc.tags))
        self.assertEqual(len([tag for tag, _ in doc.tags if tag == "img"]), 1)
        self.assertFalse(any(name.startswith("on") for _, attrs in doc.tags for name in attrs))
        self.assertEqual([a for t, a in doc.tags if t == "img"][0]["alt"], attack)

    def test_chart_uses_the_declared_maximum_from_a_zero_baseline(self):
        for variant in FAMILIES["benchmark"]:
            doc = Document(self.render("benchmark", variant))
            bars = [attrs for _, attrs in doc.tags if "bar" in attrs.get("class", "").split()]
            self.assertEqual([bar["style"] for bar in bars], ["width:25%", "width:75%"])
            self.assertTrue(all(bar["data-maximum"] == "200" for bar in bars))
            self.assertTrue(all(bar["data-baseline"] == "0" for bar in bars))
            self.assertIn("bar-emphasis", bars[-1]["class"].split())
            self.assertIn("Matched conditions; publisher reported", doc.text)

    def test_offer_always_shows_all_terms_and_archive_status_in_both_variants(self):
        for variant in FAMILIES["offer"]:
            text = Document(self.render("offer", variant)).text
            for required in ("Six months of Studio", "Verified library members", "31 December 2026", "Archived offer"):
                self.assertIn(required, text)

    def test_source_and_asset_credit_are_visible_with_illustration_qualification(self):
        spec = story("financial")
        spec["asset"] = copy.deepcopy(story("product")["asset"])
        spec["asset"]["kind"] = "editorial_illustration"
        doc = Document(self.render("financial", spec=spec, image=IMAGE))
        self.assertIn("Orbit announcement", doc.text)
        self.assertIn("Orbit media kit", doc.text)
        self.assertIn("Editorial illustration", doc.text)
        plain = Document(self.render("financial"))
        self.assertFalse(any(tag == "img" for tag, _ in plain.tags))

    def test_fonts_and_assets_are_embedded_without_remote_requests_or_scripts(self):
        html = self.render("product", image=IMAGE)
        doc = Document(html)
        self.assertEqual(len(re.findall(r"url\(['\"]?data:font/ttf;base64,", html)), 3)
        self.assertNotRegex(html, r"url\(['\"]?https?://")
        self.assertFalse(any(tag in ("script", "link", "iframe") for tag, _ in doc.tags))
        self.assertTrue(all(attrs["src"].startswith("data:image/") for tag, attrs in doc.tags if tag == "img"))

    def test_product_without_normalized_image_and_arbitrary_styles_fail_closed(self):
        with self.assertRaises(ValueError):
            self.render("product")
        with self.assertRaises(ValueError):
            self.render("product", image="https://example.org/image.png")
        with self.assertRaises(ValueError):
            build_html(story("offer"), {"family": "offer", "variant": 'poster" onclick="bad', "palette": "acid"})
        with self.assertRaises(ValueError):
            build_html(story("offer"), {"family": "offer", "variant": "poster", "palette": "red;display:none"})

    def test_policy_preserves_reported_or_alleged_status(self):
        for status in ("reported", "confirmed", "alleged"):
            spec = story("policy")
            spec["content"]["policy"]["status"] = status
            for variant in FAMILIES["policy"]:
                text = Document(self.render("policy", variant, spec=spec)).text.lower()
                self.assertIn(status, text)
                self.assertIn("requests a review", text)
                self.assertIn("orbit labs", text)


if __name__ == "__main__":
    unittest.main()

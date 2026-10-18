"""Story briefs must remain truthful, bounded and varied across real publications."""

import copy
import json
import unittest
from pathlib import Path

from visuals.selection import eligible_families, select_style
from visuals.spec import validate_spec


FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name="benchmark"):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def published(style, **overrides):
    record = {"status": 201, "media_ids": ["123"], "dry_run": False, "visual": style}
    record.update(overrides)
    return record


class BriefValidationTests(unittest.TestCase):
    def test_all_six_fresh_fixtures_validate_without_injecting_news(self):
        for family in ("benchmark", "product", "offer", "financial", "policy", "research"):
            with self.subTest(family=family):
                raw = fixture(family)
                original = copy.deepcopy(raw)
                validated = validate_spec(raw)
                self.assertEqual(validated["headline"], original["headline"])
                self.assertEqual(raw, original)
                self.assertEqual(validated["content"][family]["source_url"], raw["source"]["url"])
                self.assertIn("DEMO", validated["headline"])

    def test_benchmark_values_inherit_source_and_preserve_explicit_sources(self):
        raw = fixture()
        raw["content"]["benchmark"]["values"][1]["source_url"] = "https://example.org/method"
        result = validate_spec(raw)["content"]["benchmark"]
        self.assertEqual(result["values"][0]["source_url"], "https://example.com/demo-evaluation")
        self.assertEqual(result["values"][1]["source_url"], "https://example.org/method")

    def test_rejects_unknown_fields_at_every_level(self):
        paths = [(), ("source",), ("content",), ("content", "benchmark"),
                 ("content", "benchmark", "values", 0)]
        for path in paths:
            raw = fixture()
            obj = raw
            for part in path:
                obj = obj[part]
            obj["html"] = "<script>alert(1)</script>"
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_spec(raw)

    def test_rejects_wrong_root_types_and_version_bool(self):
        for raw in (None, [], "story", {"version": True}, {**fixture(), "version": True},
                    {**fixture(), "subject": 1}, {**fixture(), "story_id": "../../escape"}):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                validate_spec(raw)

    def test_rejects_oversized_control_and_markup_fields(self):
        for value in ("x" * 97, "", "Bad\x00headline", "<svg onload=alert(1)>", "Hello\nworld"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_spec({**fixture(), "headline": value})

    def test_rejects_unknown_story_type_family_and_palette(self):
        for key, value in (("story_type", "anything"), ("preferred_family", "random"), ("palette", "url(x)")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_spec({**fixture(), key: value})

    def test_requires_https_public_hostname_urls_without_credentials(self):
        invalid = ["http://example.com", "javascript:alert(1)", "https://user:pass@example.com",
                   "https://localhost/item", "https://127.0.0.1/a", "https://[::1]/a", "https://example.com:444/a"]
        for url in invalid:
            raw = fixture()
            raw["source"]["url"] = url
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_spec(raw)

    def test_rejects_uncomparable_or_misleading_benchmark_scales(self):
        for key, value in (("comparable", False), ("maximum", 0), ("maximum", float("inf")),
                           ("maximum", True), ("values", [{"label": "Only one", "value": 1}])):
            raw = fixture()
            raw["content"]["benchmark"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_spec(raw)
        for value in (-1, 101, float("nan"), True, "42"):
            raw = fixture()
            raw["content"]["benchmark"]["values"][0]["value"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_spec(raw)

    def test_rejects_duplicate_benchmark_labels(self):
        raw = fixture()
        raw["content"]["benchmark"]["values"][1]["label"] = "Demo model A"
        with self.assertRaises(ValueError):
            validate_spec(raw)

    def test_huge_json_integers_raise_validation_error_not_overflow(self):
        raw = fixture()
        raw["content"]["benchmark"]["maximum"] = 10 ** 1000
        with self.assertRaises(ValueError):
            validate_spec(raw)

    def test_rejects_nested_sources_and_unqualified_financial_change(self):
        raw = fixture()
        raw["content"]["benchmark"]["values"][0]["source_url"] = "http://example.com/unsupported"
        with self.assertRaises(ValueError):
            validate_spec(raw)
        raw = fixture("financial")
        del raw["content"]["financial"]["change_label"]
        with self.assertRaises(ValueError):
            validate_spec(raw)

    def test_asset_requires_one_location_and_complete_provenance(self):
        for remove in ("source_url", "credit", "alt", "subject", "kind", "path"):
            raw = fixture("product")
            del raw["asset"][remove]
            with self.subTest(remove=remove), self.assertRaises(ValueError):
                validate_spec(raw)
        raw = fixture("product")
        raw["asset"]["url"] = "https://example.com/image.png"
        with self.assertRaises(ValueError):
            validate_spec(raw)

    def test_asset_rejects_unsafe_local_paths_and_unknown_kind(self):
        for value in ("../secret.png", "/tmp/test.png", "C:\\secret.png", "media/../../secret.png", "media\\x.png"):
            raw = fixture("product")
            raw["asset"]["path"] = value
            with self.subTest(path=value), self.assertRaises(ValueError):
                validate_spec(raw)
        raw = fixture("product")
        raw["asset"]["kind"] = "stock"
        with self.assertRaises(ValueError):
            validate_spec(raw)

    def test_rejects_wrong_family_types_missing_terms_and_excessive_lists(self):
        cases = [("product", "features", []), ("offer", "deadline", ""),
                 ("offer", "archived", "yes"), ("financial", "value", 42),
                 ("policy", "status", "proven"), ("policy", "targets", ["a"] * 4),
                 ("research", "steps", [{"title": "One", "detail": "One step"}])]
        for family, key, value in cases:
            raw = fixture(family)
            raw["content"][family][key] = value
            with self.subTest(family=family, key=key), self.assertRaises(ValueError):
                validate_spec(raw)


class SelectionTests(unittest.TestCase):
    def test_selects_only_story_relevant_supplied_content(self):
        expected = {"benchmark": "benchmark", "product": "product", "offer": "offer",
                    "financial": "financial", "policy": "policy", "research": "research"}
        for name, family in expected.items():
            with self.subTest(name=name):
                spec = validate_spec(fixture(name))
                self.assertEqual(eligible_families(spec), [family])
                self.assertEqual(select_style(spec, [])["family"], family)

    def test_no_visual_is_better_than_inventing_a_family(self):
        spec = fixture()
        spec["content"] = {}
        self.assertEqual(eligible_families(validate_spec(spec)), [])
        self.assertIsNone(select_style(validate_spec(spec), []))

    def test_product_without_asset_cannot_select_a_product_visual(self):
        spec = fixture("product")
        del spec["asset"]
        self.assertEqual(eligible_families(validate_spec(spec)), [])

    def test_offer_cannot_hide_terms_using_product_content(self):
        spec = fixture("product")
        spec["story_type"] = "offer"
        spec["preferred_family"] = "product"
        self.assertIsNone(select_style(validate_spec(spec), []))

    def test_inappropriate_family_cannot_be_forced_by_preference(self):
        spec = fixture("financial")
        spec["content"]["benchmark"] = fixture()["content"]["benchmark"]
        spec["preferred_family"] = "benchmark"
        self.assertEqual(eligible_families(validate_spec(spec)), ["financial"])
        self.assertEqual(select_style(validate_spec(spec), [])["family"], "financial")

    def test_story_type_mapping_including_quote_and_security(self):
        expected = {"model_release": ["benchmark", "product", "research"],
                    "product_launch": ["product", "benchmark", "research"], "offer": ["offer"],
                    "earnings": ["financial"], "funding": ["financial"],
                    "acquisition": ["policy", "financial"], "policy": ["policy"],
                    "security": ["policy", "research"], "research": ["research", "benchmark"],
                    "outage": ["policy", "research"], "quote": []}
        spec = fixture("product")
        spec["content"] = {name: fixture(name)["content"][name] for name in
                           ("benchmark", "product", "offer", "financial", "policy", "research")}
        for story_type, families in expected.items():
            spec["story_type"] = story_type
            with self.subTest(story_type=story_type):
                self.assertEqual(eligible_families(validate_spec(spec)), families)

    def test_deterministic_selection_with_fresh_content_and_valid_variants(self):
        variants = {"benchmark": {"split", "full"}, "product": {"split", "image-first"},
                    "offer": {"poster", "split"}, "financial": {"statement", "split"},
                    "policy": {"branch", "stack"}, "research": {"flow", "vertical"}}
        palettes = {"benchmark": "cobalt", "product": "ivory", "offer": "acid",
                    "financial": "ink", "policy": "ivory", "research": "clay"}
        for name in variants:
            spec = validate_spec(fixture(name))
            result = select_style(spec, [])
            with self.subTest(family=name):
                self.assertEqual(result, select_style(spec, []))
                self.assertIn(result["variant"], variants[name])
                self.assertEqual(result["palette"], palettes[name])

    def test_alternates_composition_after_last_successful_image(self):
        spec = validate_spec(fixture("research"))
        first = select_style(spec, [])
        second = select_style(spec, [published(first)])
        self.assertEqual(second["family"], "research")
        self.assertNotEqual(second["variant"], first["variant"])

    def test_absent_optional_mode_flags_still_count_actual_image_publications(self):
        spec = validate_spec(fixture())
        first = select_style(spec, [])
        history = [{"status": 201, "media_ids": ["123"], "visual": first}]
        self.assertNotEqual(select_style(spec, history)["variant"], first["variant"])

    def test_ignores_failed_preview_dry_run_text_only_and_bad_visual_history(self):
        spec = validate_spec(fixture())
        first = select_style(spec, [])
        bad_history = [published(first, status=500), published(first, dry_run=True),
                       published(first, preview=True), published(first, media_ids=[]),
                       published({"family": "benchmark", "variant": "injected", "palette": "cobalt"}),
                       published(first, media_ids=None)]
        self.assertEqual(select_style(spec, bad_history), first)

    def test_only_last_six_successful_images_affect_selection(self):
        spec = validate_spec(fixture())
        old = published({"family": "benchmark", "variant": "split", "palette": "cobalt"})
        recent = [published({"family": "research", "variant": "flow", "palette": "clay"})] * 6
        self.assertEqual(select_style(spec, [old] * 100 + recent), select_style(spec, recent))

    def test_recent_repetition_can_favor_another_supplied_relevant_family(self):
        spec = fixture("product")
        spec["story_type"] = "model_release"
        spec["content"]["benchmark"] = fixture()["content"]["benchmark"]
        history = [published({"family": "benchmark", "variant": "split", "palette": "cobalt"}),
                   published({"family": "benchmark", "variant": "full", "palette": "cobalt"})] * 3
        self.assertEqual(select_style(validate_spec(spec), history)["family"], "product")

    def test_malformed_history_is_ignored_without_crashing(self):
        spec = validate_spec(fixture())
        expected = select_style(spec, [])
        records = [None, [], "wrong", published({"family": [], "variant": "full", "palette": "cobalt"}),
                   published({"family": "benchmark", "variant": [], "palette": {}}),
                   published(expected, dry_run="false"), published(expected, preview="false"),
                   published(expected, status=True), published(expected, media_ids=[""])]
        self.assertEqual(select_style(spec, records), expected)

    def test_palette_is_advisory_allowlisted_and_preserved(self):
        spec = fixture()
        spec["palette"] = "ink"
        self.assertEqual(select_style(validate_spec(spec), [])["palette"], "ink")


if __name__ == "__main__":
    unittest.main()

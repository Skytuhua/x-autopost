import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from posting import send_prepared
from visuals.prepare import prepare_media
from visuals.render import inspect_layout


class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body
        self.text = json.dumps(body)

    def json(self):
        return self._body


class PostingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.prepared = {'media': [], 'warnings': [], 'generated_files': []}

    def tearDown(self):
        self.temporary.cleanup()

    def test_preview_never_creates_oauth_session_or_requests_x(self):
        factory = Mock(side_effect=AssertionError('Preview reached X'))
        result = send_prepared(self.prepared, 'Preview only', preview=True, session_factory=factory, repo_root=self.root)
        factory.assert_not_called()
        self.assertTrue(result['preview'])
        self.assertEqual(result['status'], 200)

    def test_text_only_post_sends_no_media_and_records_no_visual(self):
        session = Mock()
        session.post.return_value = FakeResponse(201, {'data': {'id': 'new-post'}})
        result = send_prepared(self.prepared, 'Fresh story', session=session, repo_root=self.root)
        self.assertEqual(session.post.call_count, 1)
        self.assertEqual(session.post.call_args.kwargs['json'], {'text': 'Fresh story'})
        self.assertEqual(result['status'], 201)
        self.assertNotIn('visual', result)

    def test_uploaded_image_metadata_is_recorded_only_on_attached_success(self):
        image = self.make_image()
        prepared = {'media': [str(image.relative_to(self.root))], 'visual': {'family': 'policy', 'variant': 'branch'}, 'warnings': []}
        session = Mock()
        session.post.side_effect = [FakeResponse(200, {'data': {'id': 'media-id'}}), FakeResponse(201, {'data': {'id': 'post-id'}})]
        result = send_prepared(prepared, 'New policy story', session=session, repo_root=self.root)
        self.assertEqual(result['visual']['family'], 'policy')
        self.assertEqual(result['media_ids'], ['media-id'])
        self.assertEqual(session.post.call_args.kwargs['json']['media']['media_ids'], ['media-id'])

    def test_failed_upload_falls_back_to_one_text_post_without_visual(self):
        image = self.make_image()
        prepared = {'media': [str(image.relative_to(self.root))], 'visual': {'family': 'product'}, 'warnings': []}
        session = Mock()
        session.post.side_effect = [FakeResponse(400, {'error': 'bad image'}), FakeResponse(201, {'data': {'id': 'text-post'}})]
        result = send_prepared(prepared, 'News still goes out', session=session, repo_root=self.root)
        self.assertEqual(session.post.call_count, 2)
        self.assertEqual(session.post.call_args.kwargs['json'], {'text': 'News still goes out'})
        self.assertEqual(result['media'], [])
        self.assertNotIn('visual', result)
        self.assertTrue(result['warnings'])

    def test_ambiguous_post_failure_is_not_retried(self):
        session = Mock()
        session.post.side_effect = TimeoutError('network timeout')
        result = send_prepared(self.prepared, 'A single attempt', session=session, repo_root=self.root)
        self.assertEqual(result['status'], 0)
        self.assertEqual(session.post.call_count, 1)
        self.assertIn('not retried', result['body'])

    def make_image(self):
        from PIL import Image
        directory = self.root / 'media' / 'generated'
        directory.mkdir(parents=True, exist_ok=True)
        image = directory / 'example.png'
        Image.new('RGB', (640, 360), '#234567').save(image)
        return image


class PreparationTests(unittest.TestCase):
    def test_valid_brief_is_prepared_with_image_and_provenance_files(self):
        fixture = Path(__file__).parent / 'fixtures/policy.json'
        def render_stub(spec, style, file, image_data_uri=None):
            from PIL import Image
            file.parent.mkdir(parents=True, exist_ok=True)
            Image.new('RGB', (1600, 900), '#456789').save(file)
            file.with_suffix('.json').write_text('{}')
            file.with_suffix('.html').write_text('<html></html>')
            Image.new('RGB', (390, 219), '#456789').save(file.with_suffix('.phone.png'))
            return {**style, 'story_id': spec['story_id']}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch('visuals.render.render_visual', side_effect=render_stub):
                result = prepare_media(visual_spec=fixture.read_text(), media='', repo_root=root,
                                       output_dir=root / 'media/generated', history_path=root / 'posted.jsonl')
            self.assertEqual(len(result['media']), 1, result['warnings'])
            self.assertEqual(result['visual']['family'], 'policy')
            self.assertEqual(len(result['generated_files']), 3)
            self.assertTrue((root / 'output/review/prepared.json').exists())

    def test_sender_cli_preview_does_not_change_publication_state(self):
        from posting import main
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'output').mkdir()
            (root / 'output/prepared.json').write_text('{"media":[],"warnings":[]}')
            (root / 'last_result.json').write_text('{"original":true}')
            (root / 'posted.jsonl').write_text('original history\n')
            try:
                os.chdir(root)
                with patch.dict(os.environ, {'VISUAL_PREVIEW': 'true', 'POST_TEXT': 'Preview'}):
                    main()
            finally:
                os.chdir(previous)
            self.assertEqual((root / 'last_result.json').read_text(), '{"original":true}')
            self.assertEqual((root / 'posted.jsonl').read_text(), 'original history\n')
            self.assertTrue((root / 'output/review/preview-result.json').exists())

    def test_invalid_brief_omits_image_and_explains_why(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result = prepare_media(visual_spec='{"version":999}', media='', repo_root=root, output_dir=root / 'media' / 'generated', history_path=root / 'posted.jsonl')
            self.assertEqual(result['media'], [])
            self.assertNotIn('visual', result)
            self.assertTrue(result['warnings'])

    def test_history_reader_ignores_corrupt_lines_without_losing_valid_records(self):
        from visuals.prepare import read_history
        with tempfile.TemporaryDirectory() as folder:
            history = Path(folder) / 'posted.jsonl'
            history.write_text('{bad json}\n' + json.dumps({'status': 201}) + '\n', encoding='utf-8')
            self.assertEqual(read_history(history), [{'status': 201}])


class LayoutTests(unittest.TestCase):
    def test_layout_report_rejects_text_overflow_and_region_collisions(self):
        page = Mock()
        page.evaluate.return_value = {'width': 1600, 'height': 900, 'issues': ['text-overflow', 'region-overlap'], 'fonts': []}
        with self.assertRaises(ValueError):
            inspect_layout(page)


if __name__ == '__main__':
    unittest.main()

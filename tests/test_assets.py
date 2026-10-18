"""Boundary tests for supplied editorial assets; no real network is used."""

import base64
from io import BytesIO
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import Mock, patch

from PIL import Image

from visuals import assets


def image_bytes(fmt="PNG", size=(160, 128), color="orange"):
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format=fmt)
    return buffer.getvalue()


class ImageNormalizationTests(unittest.TestCase):
    def test_png_jpeg_and_webp_are_normalized_to_png_without_metadata(self):
        for fmt in ("PNG", "JPEG", "WEBP"):
            with self.subTest(fmt=fmt):
                normalized = assets.validate_image_bytes(image_bytes(fmt))
                with Image.open(BytesIO(normalized)) as result:
                    self.assertEqual(result.format, "PNG")
                    self.assertEqual(result.size, (160, 128))
                    self.assertNotIn("exif", result.info)

    def test_transparency_is_preserved(self):
        buffer = BytesIO()
        Image.new("RGBA", (128, 128), (23, 30, 40, 128)).save(buffer, "PNG")
        with Image.open(BytesIO(assets.validate_image_bytes(buffer.getvalue()))) as result:
            self.assertEqual(result.getpixel((0, 0)), (23, 30, 40, 128))

    def test_corrupt_html_svg_gif_and_truncated_images_are_rejected(self):
        cases = (b"not an image", b"<html>access denied</html>", b"<svg></svg>",
                 image_bytes("GIF"), image_bytes("PNG")[:40])
        for data in cases:
            with self.subTest(data=data[:20]):
                with self.assertRaises(ValueError):
                    assets.validate_image_bytes(data)

    def test_supplied_image_minimum_edge_is_enforced(self):
        with self.assertRaisesRegex(ValueError, "128"):
            assets.validate_image_bytes(image_bytes(size=(512, 127)))

    def test_source_byte_and_pixel_edge_caps_are_enforced(self):
        with self.assertRaises(ValueError):
            assets.validate_image_bytes(b"x" * (assets.MAX_SOURCE_BYTES + 1))
        for size in ((8193, 128), (4001, 4000)):
            with self.subTest(size=size), self.assertRaises(ValueError):
                assets.validate_image_bytes(image_bytes(size=size))

    def test_final_normalized_size_cap_is_enforced(self):
        with patch.object(assets, "MAX_OUTPUT_BYTES", 30):
            with self.assertRaises(ValueError):
                assets.validate_image_bytes(image_bytes())

    def test_exif_orientation_is_applied_before_metadata_is_removed(self):
        buffer = BytesIO()
        image = Image.new("RGB", (180, 128), "orange")
        exif = Image.Exif()
        exif[274] = 6
        image.save(buffer, "JPEG", exif=exif)
        with Image.open(BytesIO(assets.validate_image_bytes(buffer.getvalue()))) as result:
            self.assertEqual(result.size, (128, 180))
            self.assertEqual(len(result.getexif()), 0)


class LocalAssetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "media").mkdir()
        (self.root / "media" / "product.png").write_bytes(image_bytes())

    def tearDown(self):
        self.temp.cleanup()

    def test_repo_local_image_becomes_png_data_uri(self):
        uri = assets.load_asset({"path": "media/product.png"}, self.root)
        self.assertTrue(uri.startswith("data:image/png;base64,"))
        self.assertEqual(base64.b64decode(uri.split(",", 1)[1]),
                         assets.validate_image_bytes(image_bytes()))

    def test_missing_traversal_absolute_hidden_and_nonimage_paths_are_rejected(self):
        paths = ("media/missing.png", "../secret.png", "media/../secret.png",
                 "C:\\secret.png", "C:secret.png", str(self.root / "media/product.png"),
                 ".git/secret.png", "media/.hidden.png", "media/image.svg", "media/file.txt")
        for value in paths:
            with self.subTest(path=value), self.assertRaises(ValueError):
                assets.load_asset({"path": value}, self.root)

    def test_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "outside.png"
            target.write_bytes(image_bytes())
            try:
                (self.root / "media/escape.png").symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("This Windows session cannot create symlinks")
            with self.assertRaises(ValueError):
                assets.load_asset({"path": "media/escape.png"}, self.root)

    def test_resolved_escape_is_rejected_even_without_symlink_privileges(self):
        with tempfile.TemporaryDirectory() as outside:
            outside_path = Path(outside) / "outside.png"
            outside_path.write_bytes(image_bytes())
            # Model the filesystem's resolved target. The real symlink test above
            # additionally verifies this through the OS when the platform permits it.
            resolved_root = self.root.resolve()
            with patch.object(Path, "resolve", side_effect=[resolved_root, outside_path]):
                with self.assertRaises(ValueError):
                    assets.load_asset({"path": "media/escape.png"}, self.root)

    def test_exactly_one_source_is_required(self):
        for value in ({}, {"path": "media/product.png", "url": "https://example.com/a.png"}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                assets.load_asset(value, self.root)


class HttpsAssetTests(unittest.TestCase):
    def public_dns(self, *_args, **_kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))]

    def test_insecure_urls_userinfo_and_nonstandard_ports_are_rejected(self):
        bad = ("http://example.com/a.png", "https://user:pass@example.com/a.png",
               "https://example.com:8443/a.png", "https://localhost/a.png",
               "https://127.0.0.1/a.png", "https://[::1]/a.png", "https://example.com\\evil/a.png")
        for url in bad:
            with self.subTest(url=url), self.assertRaises(ValueError):
                assets._validate_https_url(url)

    def test_public_hostname_rejects_any_unsafe_dns_answer(self):
        unsafe = ("127.0.0.1", "10.1.2.3", "169.254.169.254", "0.0.0.0", "192.0.2.1",
                  "::1", "fd00::1", "fe80::1", "::ffff:127.0.0.1", "224.0.0.1")
        for ip in unsafe:
            answers = self.public_dns()
            family = socket.AF_INET6 if ":" in ip else socket.AF_INET
            answers.append((family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, 443)))
            with self.subTest(ip=ip), patch.object(assets.socket, "getaddrinfo", return_value=answers):
                with self.assertRaises(ValueError):
                    assets._resolve_public_addresses("example.com")

    def test_public_dns_resolution_returns_only_pinned_addresses(self):
        with patch.object(assets.socket, "getaddrinfo", side_effect=self.public_dns):
            self.assertEqual(assets._resolve_public_addresses("example.com"), ["93.184.216.34"])

    def test_dns_failures_and_empty_answers_are_rejected(self):
        for result in ([], socket.gaierror("not found")):
            kwargs = {"side_effect": result} if isinstance(result, Exception) else {"return_value": result}
            with self.subTest(result=result), patch.object(assets.socket, "getaddrinfo", **kwargs):
                with self.assertRaises(ValueError):
                    assets._resolve_public_addresses("example.com")

    def response(self, status=200, data=None, content_type="image/png", length=None):
        data = image_bytes() if data is None else data
        response = Mock()
        response.status = status
        response.getheader.side_effect = lambda name, default=None: {
            "Content-Type": content_type,
            "Content-Length": str(len(data)) if length is None else length,
        }.get(name, default)
        stream = BytesIO(data)
        response.read.side_effect = stream.read
        response.read1.side_effect = stream.read
        return response

    def fetch_with_response(self, response):
        conn = Mock()
        conn.getresponse.return_value = response
        with patch.object(assets.socket, "getaddrinfo", side_effect=self.public_dns), \
                patch.object(assets, "_PinnedHTTPSConnection", return_value=conn) as factory:
            result = assets._fetch_https_image("https://example.com/product.png")
        return result, conn, factory

    def test_fetch_uses_verified_ip_and_original_hostname_without_auth(self):
        data, conn, factory = self.fetch_with_response(self.response())
        self.assertEqual(data, image_bytes())
        self.assertEqual(factory.call_args.args[:2], ("example.com", "93.184.216.34"))
        self.assertEqual(conn.request.call_args.args[:2], ("GET", "/product.png"))
        headers = conn.request.call_args.kwargs["headers"]
        self.assertNotIn("Authorization", headers)
        self.assertNotIn("Cookie", headers)
        conn.close.assert_called_once()

    def test_official_cdn_binary_mime_still_requires_real_decodable_image(self):
        data, _, _ = self.fetch_with_response(self.response(content_type='application/octet-stream', data=image_bytes('WEBP')))
        normalized = assets.validate_image_bytes(data)
        with Image.open(BytesIO(normalized)) as image:
            self.assertEqual(image.format, 'PNG')
        html, _, _ = self.fetch_with_response(self.response(content_type='application/octet-stream', data=b'<html>not an image</html>'))
        with self.assertRaises(ValueError):
            assets.validate_image_bytes(html)

    def test_redirects_html_status_and_oversized_headers_are_rejected(self):
        cases = (self.response(status=302), self.response(status=404),
                 self.response(content_type="text/html", data=b"<html>Oops</html>"),
                 self.response(length=str(assets.MAX_SOURCE_BYTES + 1)))
        for response in cases:
            with self.subTest(status=response.status), self.assertRaises(ValueError):
                self.fetch_with_response(response)

    def test_streaming_oversize_is_rejected_without_trusting_content_length(self):
        response = self.response(data=b"x" * (assets.MAX_SOURCE_BYTES + 1), length="1")
        with self.assertRaises(ValueError):
            self.fetch_with_response(response)

    def test_remote_asset_is_decoded_even_when_content_type_claims_image(self):
        with patch.object(assets, "_fetch_https_image", return_value=b"<html>not an image</html>"):
            with self.assertRaises(ValueError):
                assets.load_asset({"url": "https://example.com/a.png"}, Path.cwd())

    def test_tls_connection_pins_address_but_keeps_hostname_for_certificate_check(self):
        tls = Mock()
        raw_socket = Mock()
        with patch.object(assets.ssl, "create_default_context", return_value=tls), \
                patch.object(assets.socket, "create_connection", return_value=raw_socket) as connect:
            conn = assets._PinnedHTTPSConnection("example.com", "93.184.216.34", timeout=15)
            conn.connect()
        self.assertEqual(connect.call_args.args[0], ("93.184.216.34", 443))
        tls.wrap_socket.assert_called_once_with(raw_socket, server_hostname="example.com")

    def test_failed_tls_verification_closes_the_unwrapped_socket(self):
        tls = Mock()
        tls.wrap_socket.side_effect = assets.ssl.SSLError("certificate rejected")
        raw_socket = Mock()
        with patch.object(assets.ssl, "create_default_context", return_value=tls), \
                patch.object(assets.socket, "create_connection", return_value=raw_socket):
            connection = assets._PinnedHTTPSConnection("example.com", "93.184.216.34")
            with self.assertRaises(assets.ssl.SSLError):
                connection.connect()
        raw_socket.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()

"""Load untrusted story images into a small, inert PNG data URI.

Only this module performs remote asset requests. Connections use a vetted IP
address while TLS still validates the original hostname, and never use proxies,
credentials, redirects, or cookies from the runner environment.
"""

import base64
from io import BytesIO
import http.client
import ipaddress
from pathlib import Path, PureWindowsPath
import re
import socket
import ssl
import time
from urllib.parse import quote, urlsplit
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError


MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 5_000_000
MAX_PIXELS = 16_000_000
MAX_EDGE = 8192
MIN_EDGE = 128
FETCH_TIMEOUT = 15
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
# Official CDNs sometimes label WebP/PNG as generic binary. Actual format,
# dimensions and content are still verified and normalized by Pillow.
_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp", "application/octet-stream"}


def validate_image_bytes(data: bytes) -> bytes:
    """Return a metadata-free PNG, rejecting unsupported or unbounded images."""
    if not isinstance(data, bytes) or not data or len(data) > MAX_SOURCE_BYTES:
        raise ValueError("Image source must contain at most 8 MB of bytes")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as original:
                if original.format not in {"PNG", "JPEG", "WEBP"}:
                    raise ValueError("Image format must be PNG, JPEG or WEBP")
                width, height = original.size
                if min(width, height) < MIN_EDGE:
                    raise ValueError("Image edges must be at least 128 pixels")
                if max(width, height) > MAX_EDGE or width * height > MAX_PIXELS:
                    raise ValueError("Image exceeds decoded dimension limits")
                if getattr(original, "n_frames", 1) != 1:
                    raise ValueError("Animated images are unsupported")
                original.verify()
            # Reopen after verify; transpose before stripping all supplied metadata.
            with Image.open(BytesIO(data)) as original:
                oriented = ImageOps.exif_transpose(original)
                mode = "RGBA" if "A" in oriented.getbands() or "transparency" in oriented.info else "RGB"
                converted = oriented.convert(mode)
                clean = Image.new(mode, converted.size)
                clean.paste(converted)
                output = BytesIO()
                clean.save(output, format="PNG", optimize=True)
                normalized = output.getvalue()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError,
            Image.DecompressionBombWarning, ValueError) as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError("Image could not be safely decoded") from None
    if len(normalized) > MAX_OUTPUT_BYTES:
        raise ValueError("Normalized PNG exceeds 5 MB")
    return normalized


def _is_public_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return (address.is_global and not address.is_reserved and not address.is_multicast
            and not address.is_loopback and not address.is_link_local
            and not address.is_private and not address.is_unspecified)


def _validate_https_url(value: str):
    if (not isinstance(value, str) or not value or len(value) > 2048
            or any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in value)
            or "\\" in value):
        raise ValueError("Asset URL must be a bounded HTTPS URL")
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
                or parsed.password is not None or parsed.port not in (None, 443) or parsed.fragment):
            raise ValueError("Asset URL requires HTTPS port 443 without userinfo or fragments")
        host = parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()
    except (ValueError, UnicodeError):
        raise ValueError("Asset URL requires a valid public HTTPS hostname") from None
    if not host or "%" in host or host == "localhost" or host.endswith(".localhost"):
        raise ValueError("Asset URL requires a public hostname")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if (len(host) > 253 or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                                  for label in host.split("."))):
            raise ValueError("Asset URL hostname is invalid") from None
    else:
        if not _is_public_address(host):
            raise ValueError("Asset URL requires a public IP address")
    return parsed, host


def _resolve_public_addresses(host: str) -> list[str]:
    try:
        answers = socket.getaddrinfo(host, 443, family=socket.AF_UNSPEC,
                                     type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    except OSError:
        raise ValueError("Asset hostname could not be resolved") from None
    addresses = []
    for answer in answers:
        address = answer[4][0]
        # Reject the entire destination if even one answer could reach an internal
        # network; do not let address-order or fallback behavior change the policy.
        if not _is_public_address(address):
            raise ValueError("Asset hostname resolves to a non-public destination")
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        raise ValueError("Asset hostname has no usable public addresses")
    return addresses


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str, timeout: float = FETCH_TIMEOUT):
        super().__init__(host, port=443, timeout=timeout, context=ssl.create_default_context())
        self._pinned_address = address

    def connect(self):
        # create_connection receives a numeric address, never the original DNS
        # hostname. TLS retains that hostname for SNI and certificate validation.
        raw_socket = socket.create_connection((self._pinned_address, 443), self.timeout,
                                              self.source_address)
        try:
            self.sock = self._context.wrap_socket(raw_socket, server_hostname=self.host)
        except Exception:
            raw_socket.close()
            raise


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ValueError("Asset request exceeded its 15 second timeout")
    return remaining


def _fetch_https_image(value: str) -> bytes:
    parsed, host = _validate_https_url(value)
    addresses = _resolve_public_addresses(host)
    deadline = time.monotonic() + FETCH_TIMEOUT
    connection = _PinnedHTTPSConnection(host, addresses[0], timeout=_remaining(deadline))
    path = quote(parsed.path or "/", safe="/%:@!$&'()*+,;=-._~")
    if parsed.query:
        path += "?" + quote(parsed.query, safe="/%?:@!$&'()*+,;=-._~")
    try:
        connection.request("GET", path, headers={
            "User-Agent": "x-autopost/1.0 image-loader",
            "Accept": "image/png,image/jpeg,image/webp",
            "Accept-Encoding": "identity",
        })
        if connection.sock is not None:
            connection.sock.settimeout(_remaining(deadline))
        response = connection.getresponse()
        if 300 <= response.status <= 399:
            raise ValueError("Asset redirects are not allowed")
        if response.status != 200:
            raise ValueError("Asset server did not return a successful image response")
        content_type = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type not in _CONTENT_TYPES:
            raise ValueError("Asset response has an unsupported image Content-Type")
        encoding = response.getheader("Content-Encoding", "identity").strip().lower()
        if encoding not in ("", "identity"):
            raise ValueError("Encoded asset responses are unsupported")
        content_length = response.getheader("Content-Length")
        if content_length is not None:
            try:
                length = int(content_length)
            except (TypeError, ValueError):
                raise ValueError("Asset Content-Length is invalid") from None
            if length <= 0 or length > MAX_SOURCE_BYTES:
                raise ValueError("Asset source exceeds its 8 MB limit")
        chunks = []
        total = 0
        while True:
            if connection.sock is not None:
                connection.sock.settimeout(_remaining(deadline))
            # read1 performs one bounded underlying read, so the next iteration
            # can enforce a total deadline even for a slowly trickling server.
            chunk = response.read1(min(64 * 1024, MAX_SOURCE_BYTES + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_SOURCE_BYTES:
                raise ValueError("Asset source exceeds its 8 MB limit")
            chunks.append(chunk)
        if not total:
            raise ValueError("Asset response is empty")
        return b"".join(chunks)
    except (OSError, http.client.HTTPException, UnicodeError):
        raise ValueError("Asset HTTPS request failed") from None
    finally:
        connection.close()


def _read_local_image(value: str, repo_root: Path) -> bytes:
    if (not isinstance(value, str) or not value or len(value) > 1024
            or PureWindowsPath(value).drive or value.startswith(("/", "\\"))):
        raise ValueError("Asset path must be relative to the repository")
    parts = value.replace("\\", "/").split("/")
    if any(not part or part.startswith(".") or ":" in part for part in parts):
        raise ValueError("Asset path contains a hidden or traversing component")
    if Path(parts[-1]).suffix.lower() not in _IMAGE_SUFFIXES:
        raise ValueError("Asset path must use a supported image suffix")
    try:
        root = Path(repo_root).resolve(strict=True)
        candidate = root.joinpath(*parts).resolve(strict=True)
        if not candidate.is_relative_to(root) or not candidate.is_file():
            raise ValueError("Asset path must remain inside the repository")
        with candidate.open("rb") as stream:
            data = stream.read(MAX_SOURCE_BYTES + 1)
    except (OSError, RuntimeError):
        raise ValueError("Local asset is missing or unreadable") from None
    if len(data) > MAX_SOURCE_BYTES:
        raise ValueError("Asset source exceeds its 8 MB limit")
    return data


def load_asset(asset: dict, repo_root: Path) -> str:
    """Load one supplied URL or local path after spec provenance validation."""
    if not isinstance(asset, dict) or ("url" in asset) == ("path" in asset):
        raise ValueError("Asset requires exactly one URL or repository path")
    data = (_fetch_https_image(asset["url"]) if "url" in asset
            else _read_local_image(asset["path"], repo_root))
    normalized = validate_image_bytes(data)
    return "data:image/png;base64," + base64.b64encode(normalized).decode("ascii")

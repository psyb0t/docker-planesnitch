"""Tests for images.py."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from .images import (
    NOTFOUND_SUFFIX,
    VALID_TYPE_RE,
    _image_path,
    _notfound_path,
    get_type_image,
    read_image_bytes,
)


def _make_session(
    status: int,
    body: bytes = b"",
    content_type: str = "image/jpeg",
) -> MagicMock:
    resp = MagicMock()
    resp.status = status
    resp.content_type = content_type
    resp.read = AsyncMock(return_value=body)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    session = MagicMock()
    session.get = MagicMock(return_value=ctx)
    return session


class TestValidTypeRe:
    def test_accepts_normal_types(self):
        for t in ["C17", "B738", "A320", "F16", "B52", "AJET", "RFAL"]:
            assert VALID_TYPE_RE.fullmatch(t), f"should accept {t}"

    def test_rejects_path_traversal(self):
        for t in ["../etc/passwd", "F/A18", "..", "./foo", "C17.jpg"]:
            assert not VALID_TYPE_RE.fullmatch(t), f"should reject {t}"

    def test_rejects_special_chars(self):
        for t in ["C-17", "C_17", "C 17", "C17!", "", "C17\n", "C17\x00"]:
            assert not VALID_TYPE_RE.fullmatch(t), f"should reject {t!r}"

    def test_rejects_lowercase(self):
        assert not VALID_TYPE_RE.fullmatch("c17")

    def test_rejects_oversized(self):
        assert not VALID_TYPE_RE.fullmatch("A" * 9)


class TestPaths:
    def test_image_path(self):
        assert _image_path("/images", "C17") == "/images/C17.jpg"

    def test_notfound_path(self):
        expected = f"/images/C17{NOTFOUND_SUFFIX}"
        assert _notfound_path("/images", "C17") == expected


class TestReadImageBytes:
    def test_reads_file(self, tmp_path):
        f = tmp_path / "C17.jpg"
        f.write_bytes(b"\xff\xd8\xff\xe0data")
        assert read_image_bytes(str(f)) == b"\xff\xd8\xff\xe0data"

    def test_missing_file_returns_none(self, tmp_path):
        assert read_image_bytes(str(tmp_path / "nope.jpg")) is None


class TestGetTypeImage:
    def test_rejects_path_traversal(self, tmp_path):
        session = MagicMock()
        result = asyncio.run(get_type_image("../etc/passwd", str(tmp_path), session))
        assert result is None
        assert list(tmp_path.iterdir()) == []
        session.get.assert_not_called()

    def test_rejects_empty(self, tmp_path):
        session = MagicMock()
        assert asyncio.run(get_type_image("", str(tmp_path), session)) is None
        session.get.assert_not_called()

    def test_cache_hit(self, tmp_path):
        cached = tmp_path / "C17.jpg"
        cached.write_bytes(b"cached")
        session = MagicMock()
        result = asyncio.run(get_type_image("C17", str(tmp_path), session))
        assert result == str(cached)
        session.get.assert_not_called()

    def test_notfound_marker_hit(self, tmp_path):
        marker = tmp_path / f"C17{NOTFOUND_SUFFIX}"
        marker.write_text("")
        session = MagicMock()
        result = asyncio.run(get_type_image("C17", str(tmp_path), session))
        assert result is None
        session.get.assert_not_called()

    def test_successful_download(self, tmp_path):
        body = b"\xff\xd8\xff\xe0jpeg-bytes"
        session = _make_session(200, body)
        result = asyncio.run(get_type_image("B738", str(tmp_path), session))
        assert result == str(tmp_path / "B738.jpg")
        assert (tmp_path / "B738.jpg").read_bytes() == body

    def test_404_writes_marker(self, tmp_path):
        session = _make_session(404)
        result = asyncio.run(get_type_image("ZZZZ", str(tmp_path), session))
        assert result is None
        assert (tmp_path / f"ZZZZ{NOTFOUND_SUFFIX}").exists()

    def test_uppercases_input(self, tmp_path):
        session = _make_session(200, b"jpeg")
        result = asyncio.run(get_type_image("c17", str(tmp_path), session))
        assert result == str(tmp_path / "C17.jpg")

    def test_other_status_no_cache(self, tmp_path):
        session = _make_session(500)
        result = asyncio.run(get_type_image("C17", str(tmp_path), session))
        assert result is None
        assert not (tmp_path / f"C17{NOTFOUND_SUFFIX}").exists()
        assert not (tmp_path / "C17.jpg").exists()

    def test_empty_body_no_cache(self, tmp_path):
        session = _make_session(200, b"")
        result = asyncio.run(get_type_image("C17", str(tmp_path), session))
        assert result is None
        assert not (tmp_path / "C17.jpg").exists()

    def test_html_content_type_rejected(self, tmp_path):
        # Cloudflare/origin can return 200 with an HTML challenge page.
        # We must not cache that as a JPEG.
        session = _make_session(200, b"<html>bot check</html>", "text/html")
        result = asyncio.run(get_type_image("C17", str(tmp_path), session))
        assert result is None
        assert not (tmp_path / "C17.jpg").exists()

    def test_empty_content_type_rejected(self, tmp_path):
        session = _make_session(200, b"\xff\xd8\xff", "")
        result = asyncio.run(get_type_image("C17", str(tmp_path), session))
        assert result is None
        assert not (tmp_path / "C17.jpg").exists()

    def test_network_exception(self, tmp_path):
        session = MagicMock()
        session.get = MagicMock(side_effect=Exception("connection refused"))
        result = asyncio.run(get_type_image("C17", str(tmp_path), session))
        assert result is None
        assert not (tmp_path / "C17.jpg").exists()
        assert not (tmp_path / f"C17{NOTFOUND_SUFFIX}").exists()

    def test_sends_user_agent(self, tmp_path):
        session = _make_session(200, b"jpeg")
        asyncio.run(get_type_image("C17", str(tmp_path), session))
        _, kwargs = session.get.call_args
        assert "User-Agent" in kwargs["headers"]
        assert "Mozilla" in kwargs["headers"]["User-Agent"]

"""Doc8643 aircraft type image caching."""

import asyncio
import logging
import os
import re

import aiohttp

log = logging.getLogger("planesnitch")

IMAGES_DIR = os.environ.get("PLANESNITCH_IMAGES_DIR", "/images")
DOC8643_URL = "https://doc8643.com/static/img/aircraft/large/{type}.jpg"
NOTFOUND_SUFFIX = ".notfound"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
# ICAO doc 8643 designators are alphanumeric, typically 2-4 chars.
# Reject anything else so an untrusted API field can't pull off path
# traversal or write arbitrary files into the cache dir.
VALID_TYPE_RE = re.compile(r"[A-Z0-9]{1,8}")

_in_flight: dict[str, asyncio.Lock] = {}


def _image_path(images_dir: str, ac_type: str) -> str:
    return os.path.join(images_dir, f"{ac_type}.jpg")


def _notfound_path(images_dir: str, ac_type: str) -> str:
    return os.path.join(images_dir, f"{ac_type}{NOTFOUND_SUFFIX}")


async def get_type_image(
    ac_type: str,
    images_dir: str,
    session: aiohttp.ClientSession,
) -> str | None:
    """Return local path to cached doc8643 image for ac_type, or None.

    Downloads on cache miss. Stores a .notfound marker on 404 to avoid refetch.
    """
    if not ac_type:
        return None
    ac_type = ac_type.upper()
    if not VALID_TYPE_RE.fullmatch(ac_type):
        log.debug("rejecting non-conforming type designator: %r", ac_type)
        return None

    path = _image_path(images_dir, ac_type)
    if os.path.exists(path):
        return path

    marker = _notfound_path(images_dir, ac_type)
    if os.path.exists(marker):
        return None

    lock = _in_flight.setdefault(ac_type, asyncio.Lock())
    async with lock:
        if os.path.exists(path):
            return path
        if os.path.exists(marker):
            return None

        url = DOC8643_URL.format(type=ac_type)
        log.debug("fetching doc8643 image for %s: %s", ac_type, url)
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=15),
                headers={"User-Agent": USER_AGENT},
            ) as resp:
                if resp.status == 404:
                    log.debug("no doc8643 image for %s", ac_type)
                    try:
                        os.makedirs(images_dir, exist_ok=True)
                        with open(marker, "w"):
                            pass
                    except Exception:
                        log.warning(
                            "failed to write notfound marker %s",
                            marker,
                            exc_info=True,
                        )
                    return None

                if resp.status != 200:
                    log.warning("doc8643 returned %d for %s", resp.status, ac_type)
                    return None

                # Cloudflare/origin can return 200 with HTML challenge or error
                # pages. Refuse anything that isn't an image so we don't poison
                # the cache with garbage that later gets sent to Telegram.
                content_type = (resp.content_type or "").lower()
                if not content_type.startswith("image/"):
                    log.warning(
                        "doc8643 returned non-image content-type %r for %s",
                        content_type,
                        ac_type,
                    )
                    return None

                data = await resp.read()
                if not data:
                    log.warning("doc8643 returned empty body for %s", ac_type)
                    return None

                os.makedirs(images_dir, exist_ok=True)
                tmp = path + ".tmp"
                with open(tmp, "wb") as f:
                    f.write(data)
                os.replace(tmp, path)
                log.info(
                    "cached doc8643 image for %s (%d bytes)",
                    ac_type,
                    len(data),
                )
                return path
        except Exception:
            log.warning("failed to fetch doc8643 image for %s", ac_type, exc_info=True)
            return None


def read_image_bytes(path: str) -> bytes | None:
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        log.warning("failed to read cached image %s", path, exc_info=True)
        return None

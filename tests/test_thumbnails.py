from io import BytesIO

from PIL import Image

from audio_scraper.thumbnails import save_listing_thumbnail, sync_listing_thumbnails


class Response:
    status_code = 200
    headers = {"content-type": "image/jpeg"}
    url = "https://scontent-sjc.example.fbcdn.net/photo.jpg"

    def __init__(self, content: bytes):
        self.content = content


class Client:
    def __init__(self, content: bytes):
        self.content = content

    def get(self, _url):
        return Response(self.content)


def jpeg_bytes(size=(900, 600)) -> bytes:
    output = BytesIO()
    Image.new("RGB", size, "tomato").save(output, format="JPEG", quality=90)
    return output.getvalue()


def test_thumbnail_is_resized_stripped_and_saved_as_small_webp(tmp_path):
    relative = save_listing_thumbnail(
        source="facebook",
        listing_id="123",
        image_url="https://scontent-sjc.example.fbcdn.net/photo.jpg?token=secret",
        site_root=tmp_path,
        client=Client(jpeg_bytes()),
    )
    assert relative == "images/listings/facebook-123.webp"
    target = tmp_path / relative
    assert target.stat().st_size < 40_000
    with Image.open(target) as image:
        assert image.format == "WEBP"
        assert max(image.size) <= 320
        assert not image.getexif()


def test_thumbnail_rejects_unapproved_image_hosts(tmp_path):
    relative = save_listing_thumbnail(
        source="facebook",
        listing_id="123",
        image_url="https://evil.example/track.jpg",
        site_root=tmp_path,
        client=Client(jpeg_bytes()),
    )
    assert relative is None
    assert not list(tmp_path.rglob("*.webp"))


def test_thumbnail_rejects_unsafe_listing_ids(tmp_path):
    relative = save_listing_thumbnail(
        source="facebook",
        listing_id="../../outside",
        image_url="https://scontent-sjc.example.fbcdn.net/photo.jpg",
        site_root=tmp_path,
        client=Client(jpeg_bytes()),
    )
    assert relative is None
    assert not list(tmp_path.parent.glob("outside*"))


def test_sync_strips_temporary_urls_keeps_paths_and_prunes_stale_files(tmp_path):
    stale = tmp_path / "images" / "listings" / "facebook-old.webp"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"old")
    rows = [{"source": "facebook", "listing_id": "123", "image_url": "https://scontent-sjc.example.fbcdn.net/photo.jpg?token=secret"}]
    result = sync_listing_thumbnails(rows, site_root=tmp_path, client=Client(jpeg_bytes()))
    assert result == {"saved": 1, "retained": 0, "failed": 0, "pruned": 1}
    assert "image_url" not in rows[0]
    assert rows[0]["thumbnail_path"] == "images/listings/facebook-123.webp"
    assert not stale.exists()
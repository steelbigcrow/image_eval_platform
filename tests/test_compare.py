"""接口与算法的基本测试。

运行：
    python -m pytest -q
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

import comparators
from app import create_app


def make_image(color: tuple[int, int, int], size=(64, 48)) -> Image.Image:
    return Image.new("RGB", size, color)


def encode(image: Image.Image, fmt: str = "PNG") -> bytes:
    """把 PIL 图片编码成字节，便于在多个上传位之间复用。"""
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


def upload(data: bytes, filename: str) -> tuple[io.BytesIO, str]:
    """构造 werkzeug 可识别的上传项（每次调用返回独立文件对象）。"""
    return io.BytesIO(data), filename


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture()
def red_image() -> bytes:
    return encode(make_image((220, 40, 40)))


@pytest.fixture()
def blue_image() -> bytes:
    return encode(make_image((30, 60, 200)))


# ------------------------------------------------------------------ 算法层


def test_registry_contains_builtin_algorithms():
    keys = comparators.keys()
    assert {"histogram", "pixel", "ahash"} <= set(keys)


def test_identical_images_score_full():
    image = make_image((120, 180, 90))
    for key in comparators.keys():
        result = comparators.get(key).compare(image, image.copy())
        assert result.score == pytest.approx(100, abs=0.5), key


def test_comparison_result_clamps_score():
    assert comparators.ComparisonResult.from_score(180).score == 100.0
    assert comparators.ComparisonResult.from_score(-20).score == 0.0


# -------------------------------------------------------------------- 接口


def test_index_page_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "图片比对平台" in body
    assert 'value="histogram"' in body


def test_list_algorithms(client):
    payload = client.get("/api/algorithms").get_json()
    assert payload["ok"] is True
    assert any(item["key"] == "histogram" for item in payload["data"]["algorithms"])


def test_compare_same_images_returns_high_score(client, red_image):
    response = client.post(
        "/api/compare",
        data={
            "source": upload(red_image, "source.png"),
            "target": upload(red_image, "target.png"),
            "algorithm": "histogram",
        },
        content_type="multipart/form-data",
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["data"]["score"] > 95
    assert payload["data"]["source"]["width"] == 64
    assert payload["data"]["source"]["preview"].startswith("data:image/png;base64,")
    assert payload["data"]["metrics"]["bins"] == 32 * 32


def test_compare_different_images(client, red_image, blue_image):
    response = client.post(
        "/api/compare",
        data={
            "source": upload(red_image, "source.png"),
            "target": upload(blue_image, "target.png"),
        },
        content_type="multipart/form-data",
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["data"]["score"] < 50
    assert payload["data"]["level"] in {"差异明显", "差异很大"}


def test_all_algorithms_run_through_api(client, red_image, blue_image):
    for key in comparators.keys():
        response = client.post(
            "/api/compare",
            data={
                "source": upload(red_image, "source.png"),
                "target": upload(blue_image, "target.png"),
                "algorithm": key,
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 200, key
        assert 0 <= response.get_json()["data"]["score"] <= 100, key


def test_missing_upload_returns_400(client, red_image):
    response = client.post(
        "/api/compare",
        data={"source": upload(red_image, "source.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert response.get_json()["message"] == "请上传目标图片"


def test_unknown_algorithm_returns_400(client, red_image):
    response = client.post(
        "/api/compare",
        data={
            "source": upload(red_image, "source.png"),
            "target": upload(red_image, "target.png"),
            "algorithm": "not-exist",
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "未知算法" in response.get_json()["message"]


def test_unsupported_extension_returns_400(client, red_image):
    response = client.post(
        "/api/compare",
        data={
            "source": upload(red_image, "source.txt"),
            "target": upload(red_image, "target.png"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "不支持的文件类型" in response.get_json()["message"]


def test_corrupted_image_returns_400(client, red_image):
    response = client.post(
        "/api/compare",
        data={
            "source": upload(b"this-is-not-an-image", "broken.png"),
            "target": upload(red_image, "target.png"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "无法解析图片内容" in response.get_json()["message"]


def test_jpeg_upload_is_supported(client):
    jpeg = encode(make_image((10, 200, 120)), fmt="JPEG")
    response = client.post(
        "/api/compare",
        data={
            "source": upload(jpeg, "source.jpg"),
            "target": upload(jpeg, "target.jpg"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["score"] > 95


def test_transparent_png_is_flattened(client):
    rgba = Image.new("RGBA", (40, 40), (255, 0, 0, 0))
    data = encode(rgba)
    response = client.post(
        "/api/compare",
        data={
            "source": upload(data, "alpha.png"),
            "target": upload(data, "alpha.png"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["source"]["mode"] == "RGB"

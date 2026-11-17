"""Lámina para imprimir a 300 ppp: se amplía con Replicate; sin clave o si falla, el archivo de siempre."""
import io

from PIL import Image

from app import storage, upscale


def png(w, h):
    b = io.BytesIO(); Image.new("RGB", (w, h), (200, 100, 50)).save(b, format="PNG"); return b.getvalue()


def test_ampliado_queda_en_a4_a_300_ppp():
    assert upscale.to_300ppp(Image.new("RGB", (4608, 6144))).size == (2631, 3508)


def test_amplia_una_vez_y_guarda(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "JOBS", tmp_path); monkeypatch.setattr(storage, "SB_ON", False)
    monkeypatch.setenv("REPLICATE_API_TOKEN", "r8_x")
    (tmp_path / "job1").mkdir(); (tmp_path / "job1" / "result.png").write_bytes(png(1152, 1536))
    calls = []
    monkeypatch.setattr(upscale, "replicate_x4", lambda src: calls.append(1) or png(4608, 6144))
    im = Image.open(io.BytesIO(upscale.digital_file("job1")))
    assert im.size == (2631, 3508) and round(im.info["dpi"][0]) == 300
    upscale.digital_file("job1")
    assert len(calls) == 1


def test_sin_clave_o_si_falla_no_amplia(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "JOBS", tmp_path); monkeypatch.setattr(storage, "SB_ON", False)
    (tmp_path / "job1").mkdir(); (tmp_path / "job1" / "result.png").write_bytes(png(10, 10))
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    assert upscale.digital_file("job1") is None
    monkeypatch.setenv("REPLICATE_API_TOKEN", "r8_x")
    def boom(src): raise RuntimeError("caído")
    monkeypatch.setattr(upscale, "replicate_x4", boom)
    assert upscale.digital_file("job1") is None

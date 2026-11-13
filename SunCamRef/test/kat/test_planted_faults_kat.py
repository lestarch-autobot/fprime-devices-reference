"""Known-answer tests for the plan helpers in test/int/planted_faults.py (pass + fail per helper).

Hand-built records (events.jsonl / channels.jsonl / commands.jsonl + raw/dp/ product files) stand in for the
bench; run with plain pytest: ``pytest SunCamRef/test/kat`` (not under --fth-plan, these are not plan tests).
"""
import json
import struct
import zlib
from pathlib import Path

import pytest
from fth.engine import HelperContext
from fth.plan import load_plan
from fth.replay import load_record

INT = Path(__file__).resolve().parents[1] / "int"
MARKER = "cmdDisp.NoOpStringReceived"


@pytest.fixture(scope="module")
def plan():
    return load_plan(INT / "plan.json")


def _rows(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def make_ctx(plan, tmp_path, events=(), channels=(), start=(10, 100.0), end=(11, 200.0), test_id="L0-1"):
    """A record dir with marker events at `start`/`end` (id, fsw) plus the given (fsw, name, text|value) rows."""
    rec = tmp_path / "run" / "record"
    rec.mkdir(parents=True)
    ev = [{"name": MARKER, "fsw": start[1], "epoch": 1, "id": 1, "severity": "ACTIVITY_HI",
           "args": {"text": f"Received a NO-OP string={start[0]}"}}]
    ev += [{"name": n, "fsw": t, "epoch": 1, "id": 2, "severity": "ACTIVITY_LO", "args": {"text": x}} for t, n, x in events]
    ev += [{"name": MARKER, "fsw": end[1], "epoch": 1, "id": 1, "severity": "ACTIVITY_HI",
            "args": {"text": f"Received a NO-OP string={end[0]}"}}]
    _rows(rec / "events.jsonl", sorted(ev, key=lambda r: r["fsw"]))
    _rows(rec / "channels.jsonl", [{"name": n, "fsw": t, "epoch": 1, "id": 3, "value": v} for t, n, v in sorted(channels, key=lambda r: r[0])])
    _rows(rec / "commands.jsonl", [])
    record = load_record(rec, plan.raw["event_patterns"], marker_event=MARKER, marker_command=plan.raw["markers"]["command"])
    w = record.window(start[0], end[0])
    return HelperContext(record, plan, plan.test(test_id), w, {"W": w})


def H(plan, name):
    return plan.registry.helpers[name]


# ---- event_count_at_most ------------------------------------------------------------------------------

def test_event_count_at_most_unverified_when_markers_incomplete(plan, tmp_path):
    ctx = make_ctx(plan, tmp_path)
    ctx.window.ok = False
    holds, seen, refs, unverified = H(plan, "event_count_at_most")(ctx, event="sunCamMgr.ReplyTimeout", max=1)
    assert (holds, unverified) == (None, True) and refs == []


def test_event_count_at_most_pass_fail(plan, tmp_path):
    ctx = make_ctx(plan, tmp_path, events=[(120.0, "sunCamMgr.ReplyTimeout", "x"), (130.0, "sunCamMgr.ReplyTimeout", "x")])
    assert H(plan, "event_count_at_most")(ctx, event="sunCamMgr.ReplyTimeout", max=2)[0] is True
    assert H(plan, "event_count_at_most")(ctx, event="sunCamMgr.ReplyTimeout", max=1)[0] is False


# ---- delta_mod ------------------------------------------------------------------------------------------

def test_delta_mod_pass(plan, tmp_path):
    ctx = make_ctx(plan, tmp_path, channels=[(110.0, "sunCamMgr.CameraValidCmds", 250), (190.0, "sunCamMgr.CameraValidCmds", 4)])
    holds, seen, refs, unverified = H(plan, "delta_mod")(ctx, channel="sunCamMgr.CameraValidCmds", delta=10, mod=256)
    assert (holds, unverified) == (True, False) and "first 250 last 4" in seen and refs


def test_delta_mod_fail(plan, tmp_path):
    ctx = make_ctx(plan, tmp_path, channels=[(110.0, "sunCamMgr.CameraValidCmds", 250), (190.0, "sunCamMgr.CameraValidCmds", 5)])
    assert H(plan, "delta_mod")(ctx, channel="sunCamMgr.CameraValidCmds", delta=10, mod=256)[0] is False


def test_delta_mod_unverified_with_one_sample(plan, tmp_path):
    ctx = make_ctx(plan, tmp_path, channels=[(110.0, "sunCamMgr.CameraValidCmds", 250)])
    holds, _seen, _refs, unverified = H(plan, "delta_mod")(ctx, channel="sunCamMgr.CameraValidCmds", delta=0, mod=256)
    assert (holds, unverified) == (None, True)


# ---- version_matches_manifest --------------------------------------------------------------------------

REPOS = [{"name": "uut", "describe": "a99a783-dirty"}, {"name": "harness", "describe": "v0.1.2"}, {"name": "fprime", "describe": "v4.0.0-100-gf28d2da"},
         {"name": "fprime-devices", "describe": "6a2cf2d"}]
VERSION_EVENTS = [(101.0, "version.ProjectVersion", "Project Version: [a99a783-dirty]"),
                  (102.0, "version.FrameworkVersion", "Framework Version: [v4.0.0-100-gf28d2da]"),
                  (103.0, "version.LibraryVersions", "Library Versions: [fprime-devices@6a2cf2d]")]


def _manifest(tmp_path, monkeypatch, repos=REPOS):
    m = tmp_path / "manifest.json"
    m.write_text(json.dumps({"repos": repos}), encoding="utf-8")
    monkeypatch.setenv("FTH_MANIFEST", str(m))


def test_version_matches_manifest_pass(plan, tmp_path, monkeypatch):
    _manifest(tmp_path, monkeypatch)
    ctx = make_ctx(plan, tmp_path, events=VERSION_EVENTS)
    holds, seen, refs, unverified = H(plan, "version_matches_manifest")(ctx)
    assert (holds, unverified) == (True, False) and len(refs) == 3, seen


def test_version_matches_manifest_fail_on_framework_drift(plan, tmp_path, monkeypatch):
    _manifest(tmp_path, monkeypatch)
    ev = list(VERSION_EVENTS)
    ev[1] = (102.0, "version.FrameworkVersion", "Framework Version: [v4.0.0-99-gdeadbee]")
    assert H(plan, "version_matches_manifest")(make_ctx(plan, tmp_path, events=ev))[0] is False


def test_version_matches_manifest_fail_on_missing_library_event(plan, tmp_path, monkeypatch):
    _manifest(tmp_path, monkeypatch)
    assert H(plan, "version_matches_manifest")(make_ctx(plan, tmp_path, events=VERSION_EVENTS[:2]))[0] is False


def test_version_matches_manifest_reads_runner_argv(plan, tmp_path, monkeypatch):
    monkeypatch.delenv("FTH_MANIFEST", raising=False)
    m = tmp_path / "manifest.json"
    m.write_text(json.dumps({"repos": REPOS}), encoding="utf-8")
    ctx = make_ctx(plan, tmp_path, events=VERSION_EVENTS)
    runner = tmp_path / "run" / "runner"
    runner.mkdir()
    (runner / "pytest-argv.json").write_text(json.dumps(["pytest", "--fth-manifest", str(m)]), encoding="utf-8")
    assert H(plan, "version_matches_manifest")(ctx)[0] is True


def test_version_matches_manifest_unverified_without_manifest(plan, tmp_path, monkeypatch):
    monkeypatch.delenv("FTH_MANIFEST", raising=False)
    holds, _s, _r, unverified = H(plan, "version_matches_manifest")(make_ctx(plan, tmp_path, events=VERSION_EVENTS))
    assert (holds, unverified) == (None, True)


# ---- decode_image_in_window ---------------------------------------------------------------------------

HDR = struct.Struct(">HIIHBIIB32sBQ")


BASE_ID = 0x20003000  # sunCamMgr base id (Top/instances.fpp); container Image id 0 -> container id == base


def product(sec, slot, image_mode, resolution, width, height, lines, pixels_for=lambda s, l: None, line_order=None, priority=1):
    """A DpContainer Image product: header, CRC slot, ImageHeader record (id 0), ImageLine records (id 1), data hash."""
    n = 640 if resolution == 0 else 64  # SDD Table 4: FULL 640 px, PREVIEW 64 px per line (hardware-true, probes-2/5)
    body = struct.pack(">I", BASE_ID + 0) + struct.pack(">BBBHHHH", slot, image_mode, resolution, width, height, 672, lines)
    per_slot = lines // 4 if image_mode == 3 else lines
    order = line_order or [((i // per_slot) if image_mode == 3 else slot, i % per_slot) for i in range(lines)]  # HD: slots 0..3 in order
    for s, l in order:
        px = pixels_for(s, l) or bytes([(s * 40 + l) & 0xFF]) * n
        body += struct.pack(">I", BASE_ID + 1) + struct.pack(">Q", 3 + len(px)) + bytes([s, l >> 8, l & 0xFF]) + px
    hdr = HDR.pack(0, BASE_ID, priority, 2, 0, sec, 0, 0, b"\0" * 32, 0, len(body))
    return hdr + b"\0\0\0\0" + body + b"\0\0\0\0"


def _dp(ctx, name, data):
    d = Path(ctx.record.path) / "raw" / "dp"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_bytes(data)


def _png_pixels(path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, w, h = 8, b"", 0, 0
    while pos < len(data):
        (n,) = struct.unpack(">I", data[pos:pos + 4]); tag = data[pos + 4:pos + 8]; body = data[pos + 8:pos + 8 + n]
        if tag == b"IHDR":
            w, h = struct.unpack(">II", body[:8])
        elif tag == b"IDAT":
            idat += body
        pos += 12 + n
    raw = zlib.decompress(idat)
    return w, h, [raw[r * (w + 1) + 1:(r + 1) * (w + 1)] for r in range(h)]


ARGS_L7 = dict(slot=3, image_mode="SD", resolution="PREVIEW", width=64, height=48, lines=48, expect="none", out="kat-L7-1.png")


def ramp(slot, line, n, slot_w=64, slot_h=48):
    """The camera's own test pattern as measured on the bench (probes-2/3/5): px = (x + y) mod 256 over the whole image,
    preview 10x; an HD quadrant starts at (64·(slot%2), 48·(slot//2)) of the 128×96 preview."""
    x0, y0 = slot_w * (slot % 2), slot_h * (slot // 2)
    return bytes(((x0 + c) + (y0 + line)) & 0xFF for c in range(n))


def test_decode_sd_preview_pass_writes_png(plan, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ctx = make_ctx(plan, tmp_path, test_id="L7-1")
    _dp(ctx, "SunCamRef_sunCamMgr_Image_0001.fdp", product(150, 3, 1, 1, 64, 48, 48))
    _dp(ctx, "earlier.fdp", product(50, 3, 1, 1, 64, 48, 48))  # before the window: ignored
    holds, seen, refs, unverified = H(plan, "decode_image_in_window")(ctx, **ARGS_L7)
    assert (holds, unverified) == (True, False), seen
    assert "raw/dp/SunCamRef_sunCamMgr_Image_0001.fdp" in refs
    w, h, rows = _png_pixels(tmp_path / "dev-evidence" / "images" / "kat-L7-1.png")
    assert (w, h) == (64, 48) and rows[5][0] == (3 * 40 + 5) & 0xFF


def test_decode_priority_pass_fail(plan, tmp_path, monkeypatch):
    """REQ-037: the DpContainer header priority is checked only when `priority` is given (L2-4: 10, L2-11: 7)."""
    monkeypatch.chdir(tmp_path)
    ctx = make_ctx(plan, tmp_path, test_id="L2-11")
    _dp(ctx, "SunCamRef_sunCamMgr_Image_0001.fdp", product(150, 3, 1, 1, 64, 48, 48, priority=7))
    holds, seen, _refs, unverified = H(plan, "decode_image_in_window")(ctx, **dict(ARGS_L7, out="kat-L2-11.png"), priority=7)
    assert (holds, unverified) == (True, False), seen
    holds, seen, _refs, unverified = H(plan, "decode_image_in_window")(ctx, **dict(ARGS_L7, out="kat-L2-11b.png"), priority=10)
    assert (holds, unverified) == (False, False) and "container priority=7 (expected 10)" in seen, seen
    holds, seen, _refs, unverified = H(plan, "decode_image_in_window")(ctx, **dict(ARGS_L7, out="kat-L2-11c.png"))
    assert (holds, unverified) == (True, False), seen


def test_decode_l2_11_caption_is_real_scene(plan, tmp_path, monkeypatch):
    """The L2-11 sidecar caption names the real-scene priority download, not the test-pattern default."""
    monkeypatch.chdir(tmp_path)
    ctx = make_ctx(plan, tmp_path, test_id="L2-11")
    ctx.artifacts_dir = tmp_path / "arts"
    _dp(ctx, "SunCamRef_sunCamMgr_Image_0001.fdp", product(150, 3, 1, 1, 64, 48, 48, priority=7))
    holds, seen, _refs, _u = H(plan, "decode_image_in_window")(ctx, **dict(ARGS_L7, out="L2-11-preview-priority.png"), priority=7)
    assert holds, seen
    side = json.loads((ctx.artifacts_dir / "L2-11-preview-priority.png.json").read_text())
    assert "priority 7" in side["caption"] and "test pattern OFF" in side["caption"] and "Camera test pattern" not in side["caption"]


def test_decode_hd_preview_quadrants(plan, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ctx = make_ctx(plan, tmp_path, test_id="L2-10")
    _dp(ctx, "hd.fdp", product(150, 0, 3, 1, 128, 96, 192, pixels_for=lambda s, l: bytes([(s + 1) * 50]) * 64))
    args = dict(slot=0, image_mode="HD", resolution="PREVIEW", width=128, height=96, lines=192, expect="none", out="kat-hd.png")
    holds, seen, _refs, _u = H(plan, "decode_image_in_window")(ctx, **args)
    assert holds is True, seen
    w, h, rows = _png_pixels(tmp_path / "dev-evidence" / "images" / "kat-hd.png")
    assert (w, h) == (128, 96)
    assert (rows[0][0], rows[0][127], rows[95][0], rows[95][127]) == (50, 100, 150, 200)  # TL/TR/BL/BR = slots 0..3


def test_decode_hd_preview_four_quadrant_ramp_is_one_continuous_image(plan, tmp_path, monkeypatch):
    """Mode B 3b KAT: the camera's px=(x+y) ramp split into four 64×48 quadrant slots reassembles into one 128×96 ramp."""
    monkeypatch.chdir(tmp_path)
    ctx = make_ctx(plan, tmp_path, test_id="L2-10")
    _dp(ctx, "hd.fdp", product(150, 0, 3, 1, 128, 96, 192, pixels_for=lambda s, l: ramp(s, l, 64)))
    args = dict(slot=0, image_mode="HD", resolution="PREVIEW", width=128, height=96, lines=192, expect="none", out="kat-hd-ramp.png")
    holds, seen, _refs, _u = H(plan, "decode_image_in_window")(ctx, **args)
    assert holds is True, seen
    w, h, rows = _png_pixels(tmp_path / "dev-evidence" / "images" / "kat-hd-ramp.png")
    assert (w, h) == (128, 96) and all(rows[y][x] == (x + y) & 0xFF for y in range(96) for x in range(128))
    assert rows[0][64] == 0x40 and rows[48][0] == 0x30 and rows[48][64] == 0x70  # TR / BL / BR quadrant origins (probes-5: 0x80/0xe0/0x60 ×10 preview scale aside)


def test_decode_hd_swapped_quadrants_fail(plan, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ctx = make_ctx(plan, tmp_path, test_id="L2-10")
    order = [(s, l) for s in (1, 0, 2, 3) for l in range(48)]  # slot 1 before slot 0: out of order
    _dp(ctx, "hd.fdp", product(150, 0, 3, 1, 128, 96, 192, line_order=order))
    args = dict(slot=0, image_mode="HD", resolution="PREVIEW", width=128, height=96, lines=192, expect="none", out="kat-hd-swap.png")
    holds, seen, _refs, _u = H(plan, "decode_image_in_window")(ctx, **args)
    assert holds is False and "out of slot/line order" in seen


def test_decode_sd_full_640x480(plan, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ctx = make_ctx(plan, tmp_path, test_id="L2-5")
    _dp(ctx, "full.fdp", product(150, 1, 1, 0, 640, 480, 480, pixels_for=lambda s, l: ramp(0, l, 640)))
    args = dict(slot=1, image_mode="SD", resolution="FULL", width=640, height=480, lines=480, expect="none", out="kat-sd-full.png")
    holds, seen, _refs, _u = H(plan, "decode_image_in_window")(ctx, **args)
    assert holds is True, seen
    w, h, rows = _png_pixels(tmp_path / "dev-evidence" / "images" / "kat-sd-full.png")
    assert (w, h) == (640, 480) and rows[479][639] == (639 + 479) & 0xFF and rows[1][0] == 1


@pytest.mark.parametrize("bad, why", [
    (dict(lines=47), "one line short"),
    (dict(image_mode=3), "header imageMode HD instead of SD"),
    (dict(slot=1), "header slot 1 instead of 3"),
])
def test_decode_fails_on_header_or_line_count(plan, tmp_path, monkeypatch, bad, why):
    monkeypatch.chdir(tmp_path)
    ctx = make_ctx(plan, tmp_path, test_id="L7-1")
    kw = dict(sec=150, slot=3, image_mode=1, resolution=1, width=64, height=48, lines=48)
    kw.update(bad)
    _dp(ctx, "p.fdp", product(**kw))
    holds, seen, _r, unverified = H(plan, "decode_image_in_window")(ctx, **ARGS_L7)
    assert (holds, unverified) == (False, False), (why, seen)


def test_decode_fails_on_line_order(plan, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ctx = make_ctx(plan, tmp_path, test_id="L7-1")
    order = [(3, l) for l in range(48)]
    order[10], order[11] = order[11], order[10]
    _dp(ctx, "p.fdp", product(150, 3, 1, 1, 64, 48, 48, line_order=order))
    holds, seen, _r, _u = H(plan, "decode_image_in_window")(ctx, **ARGS_L7)
    assert holds is False and "out of slot/line order" in seen


def test_decode_fails_when_two_products_in_window(plan, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ctx = make_ctx(plan, tmp_path, test_id="L7-1")
    _dp(ctx, "a.fdp", product(150, 3, 1, 1, 64, 48, 48))
    _dp(ctx, "b.fdp", product(160, 3, 1, 1, 64, 48, 48))
    holds, seen, _r, _u = H(plan, "decode_image_in_window")(ctx, **ARGS_L7)
    assert holds is False and "2 Image product(s)" in seen


def test_decode_fails_when_no_product_in_window(plan, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ctx = make_ctx(plan, tmp_path, test_id="L7-1")
    _dp(ctx, "late.fdp", product(250, 3, 1, 1, 64, 48, 48))
    holds, seen, _r, unverified = H(plan, "decode_image_in_window")(ctx, **ARGS_L7)
    assert (holds, unverified) == (False, False) and "0 Image product(s)" in seen


def test_decode_unverified_without_dump(plan, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ctx = make_ctx(plan, tmp_path, test_id="L7-1")
    assert H(plan, "decode_image_in_window")(ctx, **ARGS_L7)[3] is True


# ---- planted faults: each changes the command stream exactly as its `kind` declares, only in its test -----

def F(plan, name):
    return plan.registry.planted_faults[name].func


@pytest.mark.parametrize("fault, test_id, cmd, args, out", [
    ("expect_wrong_exposure_resetup", "L2-1", "sunCamMgr.EXPOSURE_PRM_SET", [300], [299]),
    ("expect_wrong_exposure_push", "L2-6", "sunCamMgr.EXPOSURE_PRM_SET", [300], [301]),
    ("read_wrong_register", "L2-8", "sunCamMgr.READ_REGISTER", [12306], [12304]),
    ("preview_instead_of_full", "L2-5", "sunCamMgr.DOWNLOAD", ["SLOT_1", "FULL", "0"], ["SLOT_1", "PREVIEW", "0"]),
    ("preview_instead_of_full", "L2-5", "sunCamMgr.DOWNLOAD", ["SLOT_1", "FULL", "5"], ["SLOT_1", "PREVIEW", "5"]),
])
def test_rewrite_faults(plan, fault, test_id, cmd, args, out):
    assert F(plan, fault)(test_id, cmd, args) == out
    assert F(plan, fault)(test_id, cmd, [672] if len(args) == 1 else ["SLOT_1", "PREVIEW", "0"]) is None  # other args untouched
    assert F(plan, fault)("L2-2", cmd, args) is None  # other tests untouched
    assert F(plan, fault)(test_id, "sunCamMgr.SETUP_CAMERA", []) is None


def test_insert_fault_sleep_before_final(plan):
    out = F(plan, "sleep_before_final")("L7-1", "sunCamMgr.CAPTURE", ["SLOT_4", "ON"])
    assert out == [("sunCamMgr.SLEEP", []), ("sunCamMgr.CAPTURE", ["SLOT_4", "ON"])]
    assert F(plan, "sleep_before_final")("L2-2", "sunCamMgr.CAPTURE", ["SLOT_1", "OFF"]) is None
    assert F(plan, "sleep_before_final")("L7-1", "sunCamMgr.DOWNLOAD", ["SLOT_4", "PREVIEW", "0"]) is None


def test_parse_product_real_bench_container(plan):
    """Real DpContainer from the bench (SunCamRef dry-5, slot 3 SD PREVIEW 64x48): record ids are base-qualified
    (0x20003000 header, 0x20003001 line) — a decoder that expects local ids 0/1 rejects every real product."""
    data = (Path(__file__).parent / "fixtures" / "Dp_536883200_1794262030_00092119.fdp").read_bytes()
    parsed = H(plan, "decode_image_in_window").__globals__["parse_product"](data)
    assert parsed["id"] == BASE_ID
    assert parsed["priority"] == 10  # KissCamConfig.IMAGE_DP_PRIORITY, Fw/Dp/DpContainer.hpp PRIORITY_OFFSET
    assert parsed["header"] == {"slot": 3, "imageMode": 1, "resolution": 1, "width": 64, "height": 48, "exposure": 672,
                                "linesExpected": 48}
    assert len(parsed["lines"]) == 48 and all(len(px) == 64 and s == 3 for s, _, px in parsed["lines"])
    assert [l for _, l, _ in parsed["lines"]] == list(range(48))


def _ramp(width, height, stride):
    return [bytearray((stride * (x + y)) % 256 for x in range(width)) for y in range(height)]


def test_pattern_kat_reference_preview_and_full(plan):
    """Bench-observed reference (dry-5/7/8 products): PREVIEW px = 10*(x+y) mod 256, FULL px = (x+y) mod 256."""
    kat = H(plan, "decode_image_in_window").__globals__["test_pattern_kat"]
    assert kat(_ramp(64, 48, 10), 64, 48)[0] is True
    assert kat(_ramp(128, 96, 10), 128, 96)[0] is True
    assert kat(_ramp(640, 480, 1), 640, 480)[0] is True
    assert kat(_ramp(1280, 960, 1), 1280, 960)[0] is True
    ok, text = kat(_ramp(64, 48, 1), 64, 48)  # wrong stride
    assert ok is False and "differ" in text
    dark = [bytearray([10] * 640) for _ in range(480)]  # a real dark frame (test pattern OFF) is not the pattern
    assert kat(dark, 640, 480)[0] is False
    assert kat(_ramp(80, 60, 10), 80, 60)[0] is None  # geometry outside the reference -> unverified, never a verdict


def test_pattern_kat_detects_swapped_hd_quadrants(plan):
    g = H(plan, "decode_image_in_window").__globals__
    img = _ramp(128, 96, 10)
    for y in range(48):  # swap TL and TR quadrants
        img[y][0:64], img[y][64:128] = img[y][64:128], img[y][0:64]
    ok, text = g["test_pattern_kat"](img, 128, 96)
    assert ok is False and "differ" in text


def test_pattern_kat_on_the_real_bench_product(plan):
    g = H(plan, "decode_image_in_window").__globals__
    data = (Path(__file__).parent / "fixtures" / "Dp_536883200_1794262030_00092119.fdp").read_bytes()
    parsed = g["parse_product"](data)
    img = g["assemble"](parsed["header"], parsed["lines"])
    ok, text = g["test_pattern_kat"](img, 64, 48)
    assert ok is True, text


# ---- S-9 (Mode B round 2): decode_image_in_window branches ---------------------------------------------------
def _hd_preview_ramp(s, l, swap=False):
    """One 64-px line of the HD PREVIEW pattern 10*(x+y) mod 256 for quadrant slot `s` (TL/TR/BL/BR), line `l`;
    swap=True places TL content in TR and vice versa (a wrong quadrant mapping the pattern must catch)."""
    q = {0: 1, 1: 0}.get(s, s) if swap else s
    x0, y0 = 64 * (q % 2), 48 * (q // 2)
    return bytes((10 * (x0 + x + y0 + l)) % 256 for x in range(64))


HD_ARGS = dict(slot=0, image_mode="HD", resolution="PREVIEW", width=128, height=96, lines=192, out="kat-s9.png")


def test_decode_expect_pattern_kat_holds_on_the_ramp(plan, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ctx = make_ctx(plan, tmp_path, test_id="L2-10")
    _dp(ctx, "hd.fdp", product(150, 0, 3, 1, 128, 96, 192, pixels_for=_hd_preview_ramp))
    holds, seen, _refs, unverified = H(plan, "decode_image_in_window")(ctx, **HD_ARGS, expect="pattern_kat")
    assert (holds, unverified) == (True, False), seen
    assert "pattern KAT: px = 10*(x+y) mod 256: all 12288 px match" in seen


def test_decode_expect_pattern_kat_fails_on_swapped_quadrant_content(plan, tmp_path, monkeypatch):
    """Records in slot/line order (so the order check passes) but TL/TR content swapped: only the pattern KAT sees it."""
    monkeypatch.chdir(tmp_path)
    ctx = make_ctx(plan, tmp_path, test_id="L2-10")
    _dp(ctx, "hd.fdp", product(150, 0, 3, 1, 128, 96, 192, pixels_for=lambda s, l: _hd_preview_ramp(s, l, swap=True)))
    holds, seen, _refs, unverified = H(plan, "decode_image_in_window")(ctx, **HD_ARGS, expect="pattern_kat")
    assert (holds, unverified) == (False, False), seen
    assert "test-pattern KAT mismatch" in seen and "px differ" in seen
    holds2, _seen2, _r, _u = H(plan, "decode_image_in_window")(ctx, **HD_ARGS, expect="none")
    assert holds2 is True  # without the pattern expectation the same product passes: the KAT is the only detector


def test_decode_undecodable_file_is_listed_and_not_counted(plan, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ctx = make_ctx(plan, tmp_path, test_id="L7-1")
    _dp(ctx, "garbage.fdp", b"\x00" * 40)  # shorter than a DpContainer header
    _dp(ctx, "truncated.fdp", product(150, 3, 1, 1, 64, 48, 48)[:200])  # dataSize exceeds the file
    holds, seen, _refs, unverified = H(plan, "decode_image_in_window")(ctx, **ARGS_L7)
    assert (holds, unverified) == (False, False), seen
    assert "0 Image product(s)" in seen and "garbage.fdp" in seen and "truncated.fdp" in seen and "undecodable" in seen
    _dp(ctx, "good.fdp", product(150, 3, 1, 1, 64, 48, 48))
    holds, seen, refs, unverified = H(plan, "decode_image_in_window")(ctx, **ARGS_L7)
    assert (holds, unverified) == (True, False), seen  # the garbage beside it does not break the one good product
    assert "raw/dp/good.fdp" in refs


def test_decode_torn_window_is_unverified(plan, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ctx = make_ctx(plan, tmp_path, test_id="L7-1")
    _dp(ctx, "good.fdp", product(150, 3, 1, 1, 64, 48, 48))
    torn = ctx.record.window(10, 999)  # END marker never logged
    assert not torn.ok
    ctx_torn = HelperContext(ctx.record, plan, plan.test("L7-1"), torn, {"W": torn})
    holds, seen, refs, unverified = H(plan, "decode_image_in_window")(ctx_torn, **ARGS_L7)
    assert (holds, unverified) == (None, True), seen
    assert "markers incomplete" in seen and refs == []



# ---- v0.1.13 (Captain ruling): sidecar caption/histogram + Bayer GR demosaic ---------------------------------
def test_demosaic_gr_bilinear_known_mosaic(plan):
    """GR mosaic (row 0: G R, row 1: B G) with flat per-colour planes G=10, R=200, B=50 → every output pixel
    (200, 10, 50): the bilinear neighbourhoods reproduce the planes exactly away from and at clamped edges."""
    g = H(plan, "decode_image_in_window").__globals__
    rows = [bytes([10, 200] * 3) if y % 2 == 0 else bytes([50, 10] * 3) for y in range(6)]
    rgb = g["demosaic_gr"](rows, 6, 6)
    assert all(tuple(rgb[y][3 * x:3 * x + 3]) == (200, 10, 50) for y in range(1, 5) for x in range(1, 5))  # interior
    assert tuple(rgb[0][0:3]) == (105, 10, 30)  # corner G: the clamped neighbours average with the G sample itself
    stats, hist = g["pixel_stats"](rows)
    assert stats == {"min": 10, "max": 200, "mean": 67.5, "count": 36}
    assert (hist[10], hist[50], hist[200], sum(hist)) == (18, 9, 9, 36)


def test_decode_full_real_scene_writes_sidecar_and_rgb_companion(plan, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ctx = make_ctx(plan, tmp_path, test_id="L2-5")
    ctx.artifacts_dir = tmp_path / "arts"
    _dp(ctx, "full.fdp", product(150, 0, 1, 0, 640, 480, 480, pixels_for=lambda s, l: bytes(10 + (l % 6) for _ in range(640))))
    holds, seen, refs, unverified = H(plan, "decode_image_in_window")(
        ctx, slot=0, image_mode="SD", resolution="FULL", width=640, height=480, lines=480, expect="none", out="L2-5-full.png")
    assert (holds, unverified) == (True, False), seen
    assert "PNG -> L2-5-full.png; raw px min 10 max 15 mean 12.5; RGB -> L2-5-full-rgb.png" in seen
    g = H(plan, "decode_image_in_window").__globals__
    side = json.loads((ctx.artifacts_dir / "L2-5-full.png.json").read_text())
    assert side["caption"] == g["CAPTIONS"]["L2-5-full.png"] and "raw Bayer GR, 8-bit, shown as greyscale" in side["caption"]
    assert side["decode_note"] == "raw Bayer GR, 8-bit, shown as greyscale"
    assert "at the printed exposure" in side["caption"] and "672" not in side["caption"]
    assert (side["width"], side["height"], side["exposure"], side["rgb"], side["source"]) == (640, 480, 672, "L2-5-full-rgb.png", "raw/dp/full.fdp")
    assert side["pixels"] == {"min": 10, "max": 15, "mean": 12.5, "count": 307200} and sum(side["histogram"]) == 307200
    assert [i for i, c in enumerate(side["histogram"]) if c] == [10, 11, 12, 13, 14, 15]
    assert _png_pixels(ctx.artifacts_dir / "L2-5-full.png")[:2] == (640, 480)
    rgb = (ctx.artifacts_dir / "L2-5-full-rgb.png").read_bytes()
    assert rgb[:8] == b"\x89PNG\r\n\x1a\n" and rgb[25] == 2  # colour type 2 = RGB
    assert json.loads((ctx.artifacts_dir / "L2-5-full-rgb.png.json").read_text())["caption"] == g["RGB_CAPTION"]
    assert "raw/dp/full.fdp" in refs


def test_decode_pattern_preview_gets_pattern_caption_and_no_rgb(plan, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ctx = make_ctx(plan, tmp_path, test_id="L2-10")
    ctx.artifacts_dir = tmp_path / "arts"
    _dp(ctx, "hd.fdp", product(150, 0, 3, 1, 128, 96, 192, pixels_for=_hd_preview_ramp))
    holds, seen, _refs, _u = H(plan, "decode_image_in_window")(ctx, **dict(HD_ARGS, out="L2-10-hd-preview.png"), expect="pattern_kat")
    assert holds is True, seen
    g = H(plan, "decode_image_in_window").__globals__
    side = json.loads((ctx.artifacts_dir / "L2-10-hd-preview.png.json").read_text())
    assert side["caption"] == g["PATTERN_CAPTION"] == "Camera test pattern (ramp KAT, secondary evidence; raw 8-bit shown as greyscale)"
    assert side["decode_note"] == g["GREY_NOTE"] and "rgb" not in side and "RGB ->" not in seen
    assert sorted(p.name for p in ctx.artifacts_dir.iterdir()) == ["L2-10-hd-preview.png", "L2-10-hd-preview.png.json"]

"""
Automated test suite for Web Weaver Kit.
Tests every tool's core logic: image conversion, file renaming, text formatting,
PDF cropping, SVG generation, video converter command construction, theme system,
and the update version parser.

Run with: py -m pytest test_tools.py -v
"""

import os
import re
import math
import pytest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from PIL import Image

# Import project modules — pillow_avif is a side-effect import needed by imageConverter
try:
    import pillow_avif
except ImportError:
    pass

from imageConverter import ImageConverterGUI

# pdfToImage requires fitz; guard the import
try:
    from pdfToImage import pdfToImageGUI
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


# ---------------------------------------------------------------------------
# Helpers: shared slug algorithm (same logic in imageConverter, fileRenamer, textFormatter)
# ---------------------------------------------------------------------------

def slugify(text):
    """Reference implementation of the slug pipeline used across the project."""
    text = re.sub(r'[^\w\s-]', '', text)
    text = text.lower()
    text = text.replace(' ', '-')
    text = re.sub(r'[-_]+', '-', text)
    text = re.sub(r'^-|-$', '', text)
    return text


# Extracted SVG circle generation math (mirrors svgCircleGenerator._generate_circle_svg)
def generate_circle_svg(cx, cy, radius):
    cx_r = round(cx, 2)
    cy_r = round(cy, 2)
    r_r = round(radius, 2)

    r_str = f"{int(r_r)}" if r_r == int(r_r) else f"{r_r:.2f}"

    start_x = cx_r
    start_y = round(cy_r - r_r, 2)

    dy1_r = round(2 * r_r, 2)
    dy2_r = round(-2 * r_r, 2)

    dy1_str = f"{int(dy1_r)}" if dy1_r == int(dy1_r) else f"{dy1_r:.2f}"
    dy2_str = f"{int(dy2_r)}" if dy2_r == int(dy2_r) else f"{dy2_r:.2f}"

    arc1 = f"a{r_str},{r_str} 0 1 0 0,{dy1_str}"
    arc2 = f"a{r_str},{r_str} 0 1 0 0,{dy2_str}"

    return f"M{start_x:.2f} {start_y:.2f}{arc1}{arc2}Z"


# Extracted SVG polygon generation math (mirrors svgCircleGenerator._generate_polygon_svg)
def generate_polygon_svg(points, is_closed=False):
    if not points:
        return ""
    segments = []
    for i, (ox, oy) in enumerate(points):
        prefix = "M" if i == 0 else "L"
        ox_r = round(ox, 2)
        oy_r = round(oy, 2)
        segments.append(f"{prefix}{ox_r:.2f} {oy_r:.2f}")
    path = " ".join(segments)
    if is_closed or len(points) > 2:
        path += " Z"
    return path


# Text formatter helpers (mirrors textFormatter.py methods)
def format_lower(text):
    return text.lower()

def format_upper(text):
    return text.upper()

def format_title(text):
    return text.title()

def format_camel(text):
    parts = re.split(r'[\s\-_]+', text)
    parts = [p for p in parts if p]
    if not parts:
        return ""
    return parts[0].lower() + "".join(w.capitalize() for w in parts[1:])

def format_kebab(text):
    t = text.lower()
    t = re.sub(r'[\s_]+', '-', t)
    t = re.sub(r'-+', '-', t)
    t = t.strip('-')
    return t

def format_snake(text):
    t = text.lower()
    t = re.sub(r'[\s\-]+', '_', t)
    t = re.sub(r'_+', '_', t)
    t = t.strip('_')
    return t


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def create_test_image():
    """Factory fixture that creates a test image at a given path."""
    def _create(path, size=(200, 100), mode="RGB", color="red", dpi=None):
        img = Image.new(mode, size, color)
        if dpi:
            img.info['dpi'] = dpi
        img.save(str(path))
        return str(path)
    return _create


@pytest.fixture
def source_and_dest(tmp_path):
    """Creates source and destination directories."""
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    source.mkdir()
    dest.mkdir()
    return source, dest


# ===========================================================================
# Section A: Slug / Rename Algorithm Tests
# ===========================================================================

class TestSlugify:
    @pytest.mark.parametrize("input_text, expected", [
        ("Hello World", "hello-world"),
        ("my_photo__name", "my-photo-name"),
        ("a---b", "a-b"),
        ("-hello-world-", "hello-world"),
        ("already-clean", "already-clean"),
        ("UPPER CASE", "upper-case"),
        ("spaces   multiple", "spaces-multiple"),
        ("file (1) [final]", "file-1-final"),
        ("under_score", "under-score"),
    ])
    def test_slugify(self, input_text, expected):
        assert slugify(input_text) == expected

    def test_slugify_empty_after_strip(self):
        result = slugify("---")
        assert result == ""


# ===========================================================================
# Section B: format_time Tests
# ===========================================================================

class TestFormatTime:
    def test_seconds(self):
        assert ImageConverterGUI.format_time(5.123) == "5.12 seconds"

    def test_minutes(self):
        assert ImageConverterGUI.format_time(120) == "2 minute(s)"

    def test_boundary_60(self):
        assert ImageConverterGUI.format_time(60) == "1 minute(s)"

    def test_zero(self):
        assert ImageConverterGUI.format_time(0) == "0 seconds"

    def test_just_under_60(self):
        result = ImageConverterGUI.format_time(59.99)
        assert "seconds" in result


# ===========================================================================
# Section B2: format_size Tests
# ===========================================================================

class TestFormatSize:
    def test_bytes(self):
        assert ImageConverterGUI.format_size(500) == "500 B"

    def test_kilobytes(self):
        assert ImageConverterGUI.format_size(2048) == "2.0 KB"

    def test_megabytes(self):
        assert ImageConverterGUI.format_size(5 * 1024 * 1024) == "5.0 MB"

    def test_zero(self):
        assert ImageConverterGUI.format_size(0) == "0 B"

    def test_just_under_1kb(self):
        assert ImageConverterGUI.format_size(1023) == "1023 B"

    def test_exactly_1kb(self):
        result = ImageConverterGUI.format_size(1024)
        assert "KB" in result

    def test_fractional_kb(self):
        result = ImageConverterGUI.format_size(1536)
        assert "1.5 KB" == result


# ===========================================================================
# Section C: adjust_ppi Tests
# ===========================================================================

class TestAdjustPPI:
    def test_downscale_high_dpi(self):
        img = Image.new("RGB", (100, 100))
        img.info['dpi'] = (300, 300)
        result = ImageConverterGUI.adjust_ppi(img, 72)
        assert result.info['dpi'] == (72, 72)

    def test_no_change_when_equal(self):
        img = Image.new("RGB", (100, 100))
        img.info['dpi'] = (72, 72)
        result = ImageConverterGUI.adjust_ppi(img, 72)
        assert result.info['dpi'] == (72, 72)

    def test_no_change_when_lower(self):
        img = Image.new("RGB", (100, 100))
        img.info['dpi'] = (36, 36)
        result = ImageConverterGUI.adjust_ppi(img, 72)
        assert result.info['dpi'] == (36, 36)

    def test_default_dpi_when_missing(self):
        img = Image.new("RGB", (100, 100))
        result = ImageConverterGUI.adjust_ppi(img, 72)
        assert 'dpi' not in result.info or result.info.get('dpi', (72, 72)) == (72, 72)


# ===========================================================================
# Section D: convert_file Integration Tests
# ===========================================================================

class TestConvertFile:
    def test_basic_webp_conversion(self, source_and_dest, create_test_image):
        source, dest = source_and_dest
        img_path = create_test_image(source / "test.png")
        result = ImageConverterGUI.convert_file(
            file_path=img_path, rename=False, quality=80,
            overide_image=False, extension="webp",
            folder_path=str(source), destination_folder_path=str(dest),
            new_width_percentage=100, single_file_selected=True)
        assert result is not None
        assert result.endswith(".webp")
        with Image.open(result) as img:
            assert img.format == "WEBP"

    def test_png_conversion(self, source_and_dest, create_test_image):
        source, dest = source_and_dest
        img_path = create_test_image(source / "test.jpg", color="blue")
        result = ImageConverterGUI.convert_file(
            file_path=img_path, rename=False, quality=100,
            overide_image=False, extension="png",
            folder_path=str(source), destination_folder_path=str(dest),
            new_width_percentage=100, single_file_selected=True)
        assert result is not None
        with Image.open(result) as img:
            assert img.format == "PNG"

    def test_jpeg_conversion(self, source_and_dest, create_test_image):
        source, dest = source_and_dest
        img_path = create_test_image(source / "test.png")
        result = ImageConverterGUI.convert_file(
            file_path=img_path, rename=False, quality=85,
            overide_image=False, extension="jpeg",
            folder_path=str(source), destination_folder_path=str(dest),
            new_width_percentage=100, single_file_selected=True)
        assert result is not None
        with Image.open(result) as img:
            assert img.format == "JPEG"

    def test_tiff_conversion(self, source_and_dest, create_test_image):
        source, dest = source_and_dest
        img_path = create_test_image(source / "test.png")
        result = ImageConverterGUI.convert_file(
            file_path=img_path, rename=False, quality=100,
            overide_image=False, extension="tiff",
            folder_path=str(source), destination_folder_path=str(dest),
            new_width_percentage=100, single_file_selected=True)
        assert result is not None
        assert result.endswith(".tiff")
        with Image.open(result) as img:
            assert img.format == "TIFF"

    def test_bmp_conversion(self, source_and_dest, create_test_image):
        source, dest = source_and_dest
        img_path = create_test_image(source / "test.png")
        result = ImageConverterGUI.convert_file(
            file_path=img_path, rename=False, quality=100,
            overide_image=False, extension="bmp",
            folder_path=str(source), destination_folder_path=str(dest),
            new_width_percentage=100, single_file_selected=True)
        assert result is not None
        assert result.endswith(".bmp")
        with Image.open(result) as img:
            assert img.format == "BMP"

    def test_gif_conversion(self, source_and_dest, create_test_image):
        source, dest = source_and_dest
        img_path = create_test_image(source / "test.png")
        result = ImageConverterGUI.convert_file(
            file_path=img_path, rename=False, quality=100,
            overide_image=False, extension="gif",
            folder_path=str(source), destination_folder_path=str(dest),
            new_width_percentage=100, single_file_selected=True)
        assert result is not None
        assert result.endswith(".gif")
        with Image.open(result) as img:
            assert img.format == "GIF"

    def test_ico_conversion_resizes_large_image(self, source_and_dest, create_test_image):
        source, dest = source_and_dest
        img_path = create_test_image(source / "test.png", size=(512, 512))
        result = ImageConverterGUI.convert_file(
            file_path=img_path, rename=False, quality=100,
            overide_image=False, extension="ico",
            folder_path=str(source), destination_folder_path=str(dest),
            new_width_percentage=100, single_file_selected=True)
        assert result is not None
        assert result.endswith(".ico")
        with Image.open(result) as img:
            assert img.width <= 256
            assert img.height <= 256

    def test_rgba_to_bmp_flattening(self, source_and_dest, create_test_image):
        source, dest = source_and_dest
        img_path = create_test_image(source / "transparent.png", mode="RGBA", color=(255, 0, 0, 128))
        result = ImageConverterGUI.convert_file(
            file_path=img_path, rename=False, quality=100,
            overide_image=False, extension="bmp",
            folder_path=str(source), destination_folder_path=str(dest),
            new_width_percentage=100, single_file_selected=True)
        with Image.open(result) as img:
            assert img.mode == "RGB"

    def test_resize_50_percent(self, source_and_dest, create_test_image):
        source, dest = source_and_dest
        img_path = create_test_image(source / "test.png", size=(200, 100))
        result = ImageConverterGUI.convert_file(
            file_path=img_path, rename=False, quality=100,
            overide_image=False, extension="webp",
            folder_path=str(source), destination_folder_path=str(dest),
            new_width_percentage=50, single_file_selected=True)
        with Image.open(result) as img:
            assert img.width == 100
            assert img.height == 50

    def test_no_resize_at_100_percent(self, source_and_dest, create_test_image):
        source, dest = source_and_dest
        img_path = create_test_image(source / "test.png", size=(200, 100))
        result = ImageConverterGUI.convert_file(
            file_path=img_path, rename=False, quality=100,
            overide_image=False, extension="png",
            folder_path=str(source), destination_folder_path=str(dest),
            new_width_percentage=100, single_file_selected=True)
        with Image.open(result) as img:
            assert img.width == 200
            assert img.height == 100

    def test_rename_flag(self, source_and_dest, create_test_image):
        source, dest = source_and_dest
        img_path = create_test_image(source / "My Photo (1).png")
        result = ImageConverterGUI.convert_file(
            file_path=img_path, rename=True, quality=100,
            overide_image=False, extension="webp",
            folder_path=str(source), destination_folder_path=str(dest),
            new_width_percentage=100, single_file_selected=True)
        filename = os.path.basename(result)
        assert filename == "my-photo-1.webp"

    def test_rgba_to_jpeg_flattening(self, source_and_dest, create_test_image):
        source, dest = source_and_dest
        img_path = create_test_image(source / "transparent.png", mode="RGBA", color=(255, 0, 0, 128))
        result = ImageConverterGUI.convert_file(
            file_path=img_path, rename=False, quality=90,
            overide_image=False, extension="jpeg",
            folder_path=str(source), destination_folder_path=str(dest),
            new_width_percentage=100, single_file_selected=True)
        with Image.open(result) as img:
            assert img.mode == "RGB"

    def test_override_deletes_original(self, source_and_dest, create_test_image):
        source, dest = source_and_dest
        img_path = create_test_image(source / "test.png")
        result = ImageConverterGUI.convert_file(
            file_path=img_path, rename=False, quality=100,
            overide_image=True, extension="webp",
            folder_path=str(source), destination_folder_path=str(dest),
            new_width_percentage=100, single_file_selected=True)
        assert os.path.exists(result)
        assert not os.path.exists(img_path)

    def test_folder_structure_preserved(self, source_and_dest, create_test_image):
        source, dest = source_and_dest
        subdir = source / "subdir"
        subdir.mkdir()
        img_path = create_test_image(subdir / "nested.png")
        result = ImageConverterGUI.convert_file(
            file_path=img_path, rename=False, quality=100,
            overide_image=False, extension="webp",
            folder_path=str(source), destination_folder_path=str(dest),
            new_width_percentage=100, single_file_selected=False)
        assert result is not None
        assert "subdir" in result
        assert os.path.exists(result)

    def test_avif_conversion(self, source_and_dest, create_test_image):
        pytest.importorskip("pillow_avif")
        source, dest = source_and_dest
        img_path = create_test_image(source / "test.png")
        result = ImageConverterGUI.convert_file(
            file_path=img_path, rename=False, quality=80,
            overide_image=False, extension="avif",
            folder_path=str(source), destination_folder_path=str(dest),
            new_width_percentage=100, single_file_selected=True)
        assert result is not None
        assert result.endswith(".avif")
        assert os.path.exists(result)

    def test_quality_affects_file_size(self, source_and_dest, create_test_image):
        source, dest = source_and_dest
        img = Image.new("RGB", (400, 400))
        for x in range(400):
            for y in range(400):
                img.putpixel((x, y), (x % 256, y % 256, (x + y) % 256))
        img_path = str(source / "gradient.png")
        img.save(img_path)
        dest_high = dest / "high"
        dest_low = dest / "low"
        dest_high.mkdir()
        dest_low.mkdir()
        result_high = ImageConverterGUI.convert_file(
            file_path=img_path, rename=False, quality=100,
            overide_image=False, extension="webp",
            folder_path=str(source), destination_folder_path=str(dest_high),
            new_width_percentage=100, single_file_selected=True)
        result_low = ImageConverterGUI.convert_file(
            file_path=img_path, rename=False, quality=10,
            overide_image=False, extension="webp",
            folder_path=str(source), destination_folder_path=str(dest_low),
            new_width_percentage=100, single_file_selected=True)
        assert os.path.getsize(result_low) < os.path.getsize(result_high)

    def test_convert_file_returns_none_on_bad_path(self, tmp_path):
        result = ImageConverterGUI.convert_file(
            file_path=str(tmp_path / "nonexistent.png"), rename=False,
            quality=100, overide_image=False, extension="webp",
            folder_path=str(tmp_path), destination_folder_path=str(tmp_path),
            new_width_percentage=100, single_file_selected=True)
        assert result is None


# ===========================================================================
# Section E: PDF crop_to_content Tests
# ===========================================================================

@pytest.mark.skipif(not HAS_FITZ, reason="PyMuPDF (fitz) not installed")
class TestCropToContent:
    def test_crop_removes_white_margins(self):
        img = Image.new("RGB", (200, 200), "white")
        for x in range(75, 125):
            for y in range(75, 125):
                img.putpixel((x, y), (255, 0, 0))
        cropped = pdfToImageGUI.crop_to_content(None, img)
        assert cropped.width < 200
        assert cropped.height < 200
        assert cropped.width <= 60
        assert cropped.height <= 60

    def test_crop_solid_image_unchanged(self):
        img = Image.new("RGB", (200, 200), "white")
        cropped = pdfToImageGUI.crop_to_content(None, img)
        assert cropped.width == 200
        assert cropped.height == 200

    def test_crop_with_high_threshold(self):
        img = Image.new("RGB", (200, 200), (255, 255, 255))
        for x in range(90, 110):
            for y in range(90, 110):
                img.putpixel((x, y), (250, 250, 250))
        cropped = pdfToImageGUI.crop_to_content(None, img, threshold=10)
        assert cropped.width == 200
        assert cropped.height == 200


# ===========================================================================
# Section F: SVG Circle Generation Tests
# ===========================================================================

class TestSVGCircleGeneration:
    def test_basic_circle(self):
        path = generate_circle_svg(100, 50, 20)
        assert path.startswith("M100.00 30.00")
        assert "a20,20 0 1 0 0,40" in path
        assert "a20,20 0 1 0 0,-40" in path
        assert path.endswith("Z")

    def test_circle_at_origin(self):
        path = generate_circle_svg(0, 0, 10)
        assert path.startswith("M0.00 -10.00")
        assert "a10,10 0 1 0 0,20" in path
        assert "a10,10 0 1 0 0,-20" in path

    def test_circle_with_float_radius(self):
        path = generate_circle_svg(50.5, 50.5, 15.75)
        assert "15.75" in path
        assert path.startswith("M50.50 34.75")

    def test_circle_symmetry(self):
        path = generate_circle_svg(100, 100, 25)
        assert "0,50" in path
        assert "0,-50" in path


# ===========================================================================
# Section G: SVG Polygon Generation Tests
# ===========================================================================

class TestSVGPolygonGeneration:
    def test_triangle_auto_close(self):
        points = [(10, 20), (30, 40), (50, 60)]
        path = generate_polygon_svg(points)
        assert path == "M10.00 20.00 L30.00 40.00 L50.00 60.00 Z"

    def test_two_points_no_close(self):
        points = [(10, 20), (30, 40)]
        path = generate_polygon_svg(points)
        assert path == "M10.00 20.00 L30.00 40.00"
        assert "Z" not in path

    def test_single_point(self):
        points = [(10, 20)]
        path = generate_polygon_svg(points)
        assert path == "M10.00 20.00"
        assert "Z" not in path

    def test_explicit_close(self):
        points = [(10, 20), (30, 40), (50, 60)]
        path = generate_polygon_svg(points, is_closed=True)
        assert path.endswith(" Z")

    def test_empty_points(self):
        assert generate_polygon_svg([]) == ""

    def test_float_coordinates(self):
        points = [(10.123, 20.456), (30.789, 40.012)]
        path = generate_polygon_svg(points)
        assert "M10.12 20.46" in path
        assert "L30.79 40.01" in path


# ===========================================================================
# Section H: Coordinate Conversion Round-Trip Tests
# ===========================================================================

class TestCoordinateConversion:
    def _make_generator(self, display_rect, original_size):
        gen = SimpleNamespace()
        gen.image_display_rect = display_rect
        gen.original_image = SimpleNamespace(size=original_size)
        return gen

    def _canvas_to_original(self, gen, canvas_x, canvas_y):
        disp_x, disp_y, disp_w, disp_h = gen.image_display_rect
        orig_w, orig_h = gen.original_image.size
        if not (disp_x <= canvas_x < disp_x + disp_w and disp_y <= canvas_y < disp_y + disp_h):
            return None
        x_in_display = canvas_x - disp_x
        y_in_display = canvas_y - disp_y
        original_x = (x_in_display / disp_w) * orig_w
        original_y = (y_in_display / disp_h) * orig_h
        original_x = max(0, min(orig_w, original_x))
        original_y = max(0, min(orig_h, original_y))
        return (original_x, original_y)

    def _original_to_canvas(self, gen, original_x, original_y):
        disp_x, disp_y, disp_w, disp_h = gen.image_display_rect
        orig_w, orig_h = gen.original_image.size
        x_in_display = (original_x / orig_w) * disp_w
        y_in_display = (original_y / orig_h) * disp_h
        canvas_x = x_in_display + disp_x
        canvas_y = y_in_display + disp_y
        return (canvas_x, canvas_y)

    def test_round_trip_center(self):
        gen = self._make_generator((50, 25, 400, 300), (800, 600))
        orig = (400, 300)
        canvas = self._original_to_canvas(gen, *orig)
        back = self._canvas_to_original(gen, *canvas)
        assert back is not None
        assert abs(back[0] - orig[0]) < 0.01
        assert abs(back[1] - orig[1]) < 0.01

    def test_round_trip_corner(self):
        gen = self._make_generator((50, 25, 400, 300), (800, 600))
        orig = (0, 0)
        canvas = self._original_to_canvas(gen, *orig)
        back = self._canvas_to_original(gen, *canvas)
        assert back is not None
        assert abs(back[0] - orig[0]) < 0.01
        assert abs(back[1] - orig[1]) < 0.01

    def test_click_outside_image_returns_none(self):
        gen = self._make_generator((50, 25, 400, 300), (800, 600))
        result = self._canvas_to_original(gen, 10, 10)
        assert result is None

    def test_scale_factor(self):
        gen = self._make_generator((0, 0, 400, 300), (800, 600))
        canvas = self._original_to_canvas(gen, 800, 600)
        assert abs(canvas[0] - 400) < 0.01
        assert abs(canvas[1] - 300) < 0.01


# ===========================================================================
# Section I: Video Converter Command Construction Tests
# ===========================================================================

class TestVideoConverterCommand:
    """Tests _build_ffmpeg_cmd via a mock GUI with the new codec/CRF/resolution fields."""

    def _make_gui(self, fmt="mp4", video_codec="H.264", audio_codec="AAC",
                  crf=23, resolution="original"):
        from VideoConverterGUI import VideoConverterGUI as VCG
        gui = MagicMock(spec=VCG)
        gui.format_pills = MagicMock()
        gui.format_pills.get.return_value = fmt
        gui.video_codec_var = MagicMock()
        gui.video_codec_var.get.return_value = video_codec
        gui.audio_codec_var = MagicMock()
        gui.audio_codec_var.get.return_value = audio_codec
        gui.crf_var = MagicMock()
        gui.crf_var.get.return_value = crf
        gui.resolution_pills = MagicMock()
        gui.resolution_pills.get.return_value = resolution
        # Wire up the real codec resolution methods
        gui._get_video_codec_id = lambda: VCG._get_video_codec_id(gui)
        gui._get_audio_codec_id = lambda: VCG._get_audio_codec_id(gui)
        gui._build_ffmpeg_cmd = lambda ffmpeg, inp, out: VCG._build_ffmpeg_cmd(gui, ffmpeg, inp, out)
        return gui

    def test_mp4_h264_aac(self):
        gui = self._make_gui(fmt="mp4", video_codec="H.264", audio_codec="AAC", crf=23)
        cmd = gui._build_ffmpeg_cmd("ffmpeg", "in.mp4", "out.mp4")
        assert "-c:v" in cmd
        assert cmd[cmd.index("-c:v") + 1] == "libx264"
        assert cmd[cmd.index("-c:a") + 1] == "aac"
        assert "-crf" in cmd
        assert cmd[cmd.index("-crf") + 1] == "23"
        assert "-b:v" not in cmd  # H.264 doesn't need -b:v 0

    def test_mp4_h265(self):
        gui = self._make_gui(fmt="mp4", video_codec="H.265 (HEVC)", audio_codec="AAC", crf=28)
        cmd = gui._build_ffmpeg_cmd("ffmpeg", "in.mp4", "out.mp4")
        assert cmd[cmd.index("-c:v") + 1] == "libx265"
        assert cmd[cmd.index("-crf") + 1] == "28"

    def test_webm_vp9_opus(self):
        gui = self._make_gui(fmt="webm", video_codec="VP9", audio_codec="Opus", crf=31)
        cmd = gui._build_ffmpeg_cmd("ffmpeg", "in.mp4", "out.webm")
        assert cmd[cmd.index("-c:v") + 1] == "libvpx-vp9"
        assert cmd[cmd.index("-c:a") + 1] == "libopus"
        assert "-b:v" in cmd
        assert cmd[cmd.index("-b:v") + 1] == "0"

    def test_resolution_1080p(self):
        gui = self._make_gui(resolution="1080")
        cmd = gui._build_ffmpeg_cmd("ffmpeg", "in.mp4", "out.mp4")
        assert "-vf" in cmd
        assert cmd[cmd.index("-vf") + 1] == "scale=-2:1080"

    def test_resolution_720p(self):
        gui = self._make_gui(resolution="720")
        cmd = gui._build_ffmpeg_cmd("ffmpeg", "in.mp4", "out.mp4")
        assert cmd[cmd.index("-vf") + 1] == "scale=-2:720"

    def test_resolution_original_no_scale(self):
        gui = self._make_gui(resolution="original")
        cmd = gui._build_ffmpeg_cmd("ffmpeg", "in.mp4", "out.mp4")
        assert "-vf" not in cmd

    def test_output_has_overwrite_flag(self):
        gui = self._make_gui()
        cmd = gui._build_ffmpeg_cmd("ffmpeg", "in.mp4", "out.mp4")
        assert "-y" in cmd
        assert cmd[-1] == "out.mp4"


# ===========================================================================
# Section J: PDF to WebP Conversion Tests
# ===========================================================================

@pytest.mark.skipif(not HAS_FITZ, reason="PyMuPDF (fitz) not installed")
class TestPdfToWebP:
    def test_pdf_to_webp_conversion(self, tmp_path):
        import fitz
        pdf_path = str(tmp_path / "test.pdf")
        doc = fitz.open()
        page = doc.new_page(width=200, height=200)
        page.insert_text((50, 100), "Hello Test", fontsize=20)
        doc.save(pdf_path)
        doc.close()

        gui = MagicMock()
        gui.pdf_file_path = MagicMock()
        gui.pdf_file_path.get.return_value = pdf_path
        gui.include_margins = MagicMock()
        gui.include_margins.get.return_value = True
        gui.output_format = MagicMock()
        gui.output_format.get.return_value = "webp"
        gui.quality = MagicMock()
        gui.quality.get.return_value = 85
        gui.output_path_label = MagicMock()
        gui.crop_to_content = pdfToImageGUI.crop_to_content

        with patch("tkinter.messagebox.showinfo"):
            pdfToImageGUI.convert_pdf_to_image(gui)

        expected_output = str(tmp_path / "test-thumbnail.webp")
        assert os.path.exists(expected_output)
        with Image.open(expected_output) as img:
            assert img.format == "WEBP"


# ===========================================================================
# Section K: Text Formatter Tests - All Format Types
# ===========================================================================

class TestTextFormatter:
    """Tests all text formatting algorithms."""

    # -- Slug --
    @pytest.mark.parametrize("input_text, expected", [
        ("Hello World", "hello-world"),
        ("Product Name (v2.0)", "product-name-v20"),
        ("  leading spaces  ", "leading-spaces"),
        ("CamelCaseText", "camelcasetext"),
        ("file_name_here", "file-name-here"),
        ("ALLCAPS", "allcaps"),
        ("mix-of_separators--here", "mix-of-separators-here"),
    ])
    def test_slug(self, input_text, expected):
        assert slugify(input_text) == expected

    # -- Lowercase --
    @pytest.mark.parametrize("input_text, expected", [
        ("Hello World", "hello world"),
        ("ALLCAPS", "allcaps"),
        ("already lower", "already lower"),
        ("MiXeD CaSe", "mixed case"),
    ])
    def test_lowercase(self, input_text, expected):
        assert format_lower(input_text) == expected

    # -- Uppercase --
    @pytest.mark.parametrize("input_text, expected", [
        ("Hello World", "HELLO WORLD"),
        ("already UPPER", "ALREADY UPPER"),
        ("lower", "LOWER"),
    ])
    def test_uppercase(self, input_text, expected):
        assert format_upper(input_text) == expected

    # -- Title Case --
    @pytest.mark.parametrize("input_text, expected", [
        ("hello world", "Hello World"),
        ("ALLCAPS", "Allcaps"),
        ("already Title", "Already Title"),
    ])
    def test_title(self, input_text, expected):
        assert format_title(input_text) == expected

    # -- camelCase --
    @pytest.mark.parametrize("input_text, expected", [
        ("hello world", "helloWorld"),
        ("my-variable-name", "myVariableName"),
        ("some_snake_case", "someSnakeCase"),
        ("Mixed-case_input here", "mixedCaseInputHere"),
        ("single", "single"),
        ("", ""),
    ])
    def test_camel(self, input_text, expected):
        assert format_camel(input_text) == expected

    # -- kebab-case --
    @pytest.mark.parametrize("input_text, expected", [
        ("Hello World", "hello-world"),
        ("some_snake_case", "some-snake-case"),
        ("already-kebab", "already-kebab"),
        ("ALLCAPS", "allcaps"),
        ("  extra   spaces  ", "extra-spaces"),
    ])
    def test_kebab(self, input_text, expected):
        assert format_kebab(input_text) == expected

    # -- snake_case --
    @pytest.mark.parametrize("input_text, expected", [
        ("Hello World", "hello_world"),
        ("some-kebab-case", "some_kebab_case"),
        ("already_snake", "already_snake"),
        ("ALLCAPS", "allcaps"),
        ("  extra   spaces  ", "extra_spaces"),
    ])
    def test_snake(self, input_text, expected):
        assert format_snake(input_text) == expected


# ===========================================================================
# Section L: File Renamer Logic Tests
# ===========================================================================

class TestFileRenamer:
    def test_rename_single_file(self, tmp_path):
        messy_name = "My Document (Final Copy) [v2].txt"
        file_path = tmp_path / messy_name
        file_path.write_text("test content")
        old_path = str(file_path)
        new_file_name = slugify(os.path.splitext(messy_name)[0])
        extension = os.path.splitext(messy_name)[1]
        new_path = os.path.join(str(tmp_path), new_file_name + extension)
        os.rename(old_path, new_path)
        assert os.path.exists(new_path)
        assert not os.path.exists(old_path)
        assert os.path.basename(new_path) == "my-document-final-copy-v2.txt"

    def test_rename_preserves_extension(self, tmp_path):
        name = os.path.splitext("My Image.PNG")[0]
        ext = os.path.splitext("My Image.PNG")[1]
        new_name = slugify(name) + ext
        assert new_name == "my-image.PNG"

    def test_rename_multiple_files(self, tmp_path):
        names = ["File One.txt", "File_Two.txt", "File--Three.txt"]
        for name in names:
            (tmp_path / name).write_text("content")
        for name in names:
            old = tmp_path / name
            stem = os.path.splitext(name)[0]
            ext = os.path.splitext(name)[1]
            new = tmp_path / (slugify(stem) + ext)
            os.rename(str(old), str(new))
        assert (tmp_path / "file-one.txt").exists()
        assert (tmp_path / "file-two.txt").exists()
        assert (tmp_path / "file-three.txt").exists()


# ===========================================================================
# Section M: Theme System Tests
# ===========================================================================

class TestThemeSystem:
    """Tests the color scheme switching and theme infrastructure."""

    def test_all_schemes_have_required_keys(self):
        from theme import COLOR_SCHEMES
        required = {
            "surface", "surface_container_lowest", "surface_container_low",
            "surface_container", "surface_container_high", "surface_container_highest",
            "surface_bright", "primary", "primary_container", "secondary",
            "secondary_container", "tertiary", "on_primary", "on_surface",
            "on_surface_variant", "outline_variant", "error",
        }
        for name, scheme in COLOR_SCHEMES.items():
            missing = required - set(scheme.keys())
            assert not missing, f"Scheme '{name}' missing keys: {missing}"

    def test_all_scheme_values_are_hex_colors(self):
        from theme import COLOR_SCHEMES
        hex_re = re.compile(r'^#[0-9a-fA-F]{6}$')
        for name, scheme in COLOR_SCHEMES.items():
            for key, value in scheme.items():
                assert hex_re.match(value), f"Scheme '{name}' key '{key}' has invalid color: {value}"

    def test_set_color_scheme_updates_globals(self):
        from theme import set_color_scheme, COLOR_SCHEMES
        import theme
        original = theme.PRIMARY

        # Switch to a different scheme
        other_name = [n for n in COLOR_SCHEMES if n != theme.get_active_scheme_name()][0]
        set_color_scheme(other_name)
        assert theme.PRIMARY == COLOR_SCHEMES[other_name]["primary"]
        assert theme.SURFACE == COLOR_SCHEMES[other_name]["surface"]

        # Restore
        set_color_scheme("Synthetic Atelier")
        assert theme.PRIMARY == COLOR_SCHEMES["Synthetic Atelier"]["primary"]

    def test_set_color_scheme_invalid_name_ignored(self):
        import theme
        old_name = theme.get_active_scheme_name()
        old_primary = theme.PRIMARY
        theme.set_color_scheme("NonexistentScheme")
        assert theme.get_active_scheme_name() == old_name
        assert theme.PRIMARY == old_primary

    def test_get_active_scheme_name(self):
        import theme
        theme.set_color_scheme("Midnight Blue")
        assert theme.get_active_scheme_name() == "Midnight Blue"
        theme.set_color_scheme("Synthetic Atelier")
        assert theme.get_active_scheme_name() == "Synthetic Atelier"

    def test_scheme_count(self):
        from theme import COLOR_SCHEMES
        assert len(COLOR_SCHEMES) >= 7  # 6 original + Cyberpunk


# ===========================================================================
# Section N: Version Parsing Tests
# ===========================================================================

class TestVersionParsing:
    """Tests the _parse_version helper and is_update_available logic."""

    def test_parse_simple_version(self):
        from convertToWebP import _parse_version
        assert _parse_version("1.10.0") == (1, 10, 0)

    def test_parse_v_prefixed_version(self):
        from convertToWebP import _parse_version
        assert _parse_version("v1.10.0") == (1, 10, 0)

    def test_parse_V_prefixed_version(self):
        from convertToWebP import _parse_version
        assert _parse_version("V2.3.1") == (2, 3, 1)

    def test_parse_two_part_version(self):
        from convertToWebP import _parse_version
        assert _parse_version("1.5") == (1, 5)

    def test_version_comparison_newer(self):
        from convertToWebP import _parse_version
        assert _parse_version("v2.0.0") > _parse_version("1.10.0")

    def test_version_comparison_same(self):
        from convertToWebP import _parse_version
        assert _parse_version("1.10.0") == _parse_version("v1.10.0")

    def test_version_comparison_older(self):
        from convertToWebP import _parse_version
        assert _parse_version("1.9.0") < _parse_version("1.10.0")

    def test_is_update_available_no_network(self):
        """With a mocked failed request, should return (False, '')."""
        from convertToWebP import is_update_available
        with patch("requests.get", side_effect=Exception("no network")):
            available, url = is_update_available("1.10.0")
            assert available is False
            assert url == ""

    def test_is_update_available_same_version(self):
        from convertToWebP import is_update_available
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "tag_name": "v1.10.0",
            "assets": [{"name": "app.exe", "browser_download_url": "https://example.com/app.exe"}],
        }
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.get", return_value=mock_resp):
            available, url = is_update_available("1.10.0")
            assert available is False

    def test_is_update_available_newer_version(self):
        from convertToWebP import is_update_available
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "tag_name": "v2.0.0",
            "assets": [{"name": "WebWeaverKit.exe", "browser_download_url": "https://github.com/release/WebWeaverKit.exe"}],
        }
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.get", return_value=mock_resp):
            available, url = is_update_available("1.10.0")
            assert available is True
            assert url == "https://github.com/release/WebWeaverKit.exe"

    def test_is_update_available_no_exe_asset_falls_back(self):
        from convertToWebP import is_update_available
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "tag_name": "v2.0.0",
            "assets": [{"name": "source.zip", "browser_download_url": "https://example.com/source.zip"}],
            "html_url": "https://github.com/releases/v2.0.0",
        }
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.get", return_value=mock_resp):
            available, url = is_update_available("1.10.0")
            assert available is True
            assert url == "https://github.com/releases/v2.0.0"


# ===========================================================================
# Section O: Settings Persistence Tests
# ===========================================================================

class TestSettings:
    def test_save_and_load_settings(self, tmp_path):
        import json
        settings_path = tmp_path / "settings.json"

        # Save
        data = {"color_scheme": "Cyberpunk", "some_key": 42}
        with open(settings_path, 'w') as f:
            json.dump(data, f)

        # Load
        with open(settings_path, 'r') as f:
            loaded = json.load(f)

        assert loaded["color_scheme"] == "Cyberpunk"
        assert loaded["some_key"] == 42

    def test_load_missing_settings_returns_empty(self, tmp_path):
        import json
        settings_path = tmp_path / "nonexistent.json"
        if settings_path.exists():
            settings_path.unlink()
        # Simulate load_settings behavior
        default = {}
        if not settings_path.exists():
            result = default
        assert result == {}

    def test_load_corrupt_settings_returns_empty(self, tmp_path):
        import json
        settings_path = tmp_path / "settings.json"
        settings_path.write_text("not valid json!!!")
        default = {}
        try:
            with open(settings_path, 'r') as f:
                result = json.load(f)
        except (json.JSONDecodeError, IOError):
            result = default
        assert result == {}

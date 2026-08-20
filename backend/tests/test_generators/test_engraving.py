import pytest
from app.generators.engraving import generate_text_engraving
from app.generators.engraving_font import get_glyph, get_available_fonts, FONTS


def test_font_glyphs_coverage():
    fonts = get_available_fonts()
    assert "simplex_sans" in fonts
    assert "duplex_sans" in fonts
    assert "roman_serif" in fonts
    assert "cursive_script" in fonts
    assert "block_stencil" in fonts

    for f_id in fonts:
        assert f_id in FONTS
        g = get_glyph("A", font_name=f_id)
        assert g["w"] > 0
        assert len(g["strokes"]) > 0

    # Fallback for unknown character
    unknown = get_glyph("€", font_name="simplex_sans")
    assert unknown is not None

def test_font_selection_generation():
    for f_id in ["simplex_sans", "duplex_sans", "roman_serif", "cursive_script", "block_stencil"]:
        prog = generate_text_engraving(
            text="HELLO 123",
            font_name=f_id,
            font_size=8.0,
            target_depth_z=-0.3,
        )
        assert prog.gcode is not None
        assert "G1" in prog.gcode
        assert prog.line_count > 15


def test_linear_text_engraving():
    prog = generate_text_engraving(
        text="CNC 2026",
        layout_mode="linear",
        start_x=10.0,
        start_y=20.0,
        rotation_deg=0.0,
        align="left",
        font_size=8.0,
        letter_spacing=1.0,
        target_depth_z=-0.4,
        stepdown_z=0.2,
        retract_z=2.0,
        feed_rate_xy=800.0,
        plunge_feed=300.0,
        spindle_speed=18000,
    )
    assert prog.gcode is not None
    assert "Text Engraving" in prog.gcode
    assert "Z Layer 1/2" in prog.gcode
    assert "Z Layer 2/2" in prog.gcode
    assert "G1" in prog.gcode
    assert prog.bounds.min_z == -0.4
    assert prog.bounds.max_z == 2.0
    assert prog.bounds.min_x >= 0.0

def test_multiline_rotated_text_engraving():
    prog = generate_text_engraving(
        text="LINE 1\nLINE 2",
        layout_mode="linear",
        start_x=50.0,
        start_y=50.0,
        rotation_deg=45.0,
        align="center",
        font_size=10.0,
        target_depth_z=-0.5,
        stepdown_z=0.5,
    )
    assert prog.gcode is not None
    assert "Z Layer 1/1" in prog.gcode
    assert prog.line_count > 20

def test_arc_circular_text_engraving():
    prog = generate_text_engraving(
        text="DIAL 0 1 2 3",
        layout_mode="arc",
        center_x=60.0,
        center_y=60.0,
        arc_radius=30.0,
        start_angle_deg=90.0,
        arc_direction="clockwise",
        align="center",
        font_size=6.0,
        target_depth_z=-0.3,
        stepdown_z=0.3,
    )
    assert prog.gcode is not None
    assert "Text Engraving" in prog.gcode
    assert prog.bounds.min_x >= 0.0
    assert prog.bounds.max_x > 60.0
    assert prog.bounds.max_y > 60.0

def test_engraving_empty_text_error():
    with pytest.raises(ValueError, match="cannot be empty"):
        generate_text_engraving(text="", font_size=10.0)

def test_curve_subdivisions_sampling():
    # Coarse (1x)
    prog_coarse = generate_text_engraving(
        text="O 8 C S",
        font_name="simplex_sans",
        curve_subdivisions=1,
    )
    # Smooth (4x)
    prog_smooth = generate_text_engraving(
        text="O 8 C S",
        font_name="simplex_sans",
        curve_subdivisions=4,
    )
    # Ultra-Fine (8x)
    prog_ultra = generate_text_engraving(
        text="O 8 C S",
        font_name="simplex_sans",
        curve_subdivisions=8,
    )

    # Smooth path should have significantly higher point density / lines than coarse
    assert prog_smooth.line_count > prog_coarse.line_count
    assert prog_ultra.line_count > prog_smooth.line_count
    assert "Text Engraving" in prog_smooth.gcode


def test_cursive_script_and_all_fonts_lowercase():
    for f_id in ["simplex_sans", "duplex_sans", "roman_serif", "cursive_script", "block_stencil"]:
        prog = generate_text_engraving(
            text="The Quick Brown Fox 123!",
            font_name=f_id,
            font_size=10.0,
            target_depth_z=-0.5,
        )
        assert prog.gcode is not None
        assert "G1" in prog.gcode
        assert prog.line_count > 50



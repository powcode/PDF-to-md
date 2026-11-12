import math
import pytest
from app import create_app

def luminance(hex_color):
    hex_color = hex_color.lstrip("#")
    rgb = [int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
    rgb_lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * rgb_lin[0] + 0.7152 * rgb_lin[1] + 0.0722 * rgb_lin[2]

def contrast_ratio(c1, c2):
    l1, l2 = luminance(c1), luminance(c2)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)

def test_contrast_ratios():
    # Text pairs must meet 4.5:1
    assert contrast_ratio("#1E1B2E", "#FFF8EC") >= 4.5  # Ink on cream
    assert contrast_ratio("#FFF8EC", "#1E1B2E") >= 4.5  # Cream on ink
    assert contrast_ratio("#1E1B2E", "#FF7A45") >= 4.5  # Ink on orange
    assert contrast_ratio("#1E1B2E", "#FFC93C") >= 4.5  # Ink on yellow
    assert contrast_ratio("#1E1B2E", "#3DD6A0") >= 4.5  # Ink on mint
    assert contrast_ratio("#B3261E", "#FFF8EC") >= 4.5  # Crimson on cream

    # UI parts and focus ring must meet 3:1
    assert contrast_ratio("#1E1B2E", "#FFF8EC") >= 3.0  # Ink border on cream
    assert contrast_ratio("#2F5BEA", "#FFF8EC") >= 3.0  # Blue ring on cream (2px offset)
    assert contrast_ratio("#2F5BEA", "#1E1B2E") >= 3.0  # Blue ring on ink

def test_template_components():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        res = client.get("/")
        html = res.data.decode("utf-8")

        # Tabs ARIA
        assert 'role="tablist"' in html
        assert 'role="tab"' in html
        assert 'role="tabpanel"' in html

        # Upload zones & inputs
        assert 'id="convert-upload-zone"' in html
        assert 'id="split-upload-zone"' in html
        assert 'id="convert-file-input"' in html
        assert 'id="split-file-input"' in html

        # Buttons
        assert 'id="btn-convert"' in html
        assert 'id="btn-split"' in html

        # Split range input
        assert 'id="split-ranges"' in html
        assert 'aria-describedby="split-range-error"' in html

        # Progress bar
        assert 'role="progressbar"' in html
        assert 'aria-valuenow' in html
        assert 'aria-valuemax' in html

        # Error & Badge
        assert 'role="alert"' in html
        assert 'badge-success' in html

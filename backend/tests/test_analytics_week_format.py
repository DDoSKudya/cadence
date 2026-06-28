from apps.analytics.week_format import format_week_label


def test_format_week_label_matches_frontend():
    assert format_week_label("2026-W26") == "2026 · W26"

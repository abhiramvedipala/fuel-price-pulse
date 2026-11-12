from datetime import date

from fuelpulse.freshness import check

MONDAY = date(2026, 11, 9)


def _newest(retail, crude=date(2026, 10, 30)):
    return {"retail": retail, "crude": crude}


def test_fresh_week_is_silent():
    assert check(_newest(MONDAY), MONDAY) == ([], [])


def test_late_release_warns_but_passes():
    warnings, errors = check(_newest(date(2026, 11, 2)), MONDAY)
    assert errors == [] and len(warnings) == 1
    assert "not out yet" in warnings[0] and "2026-11-02" in warnings[0]


def test_missed_week_fails_with_the_date_and_the_limit():
    warnings, errors = check(_newest(date(2026, 10, 26)), MONDAY)
    assert warnings == [] and len(errors) == 1
    assert "2026-10-26" in errors[0] and "14 days old" in errors[0] and "limit 9" in errors[0]


def test_stalled_crude_fails_on_its_own():
    _, errors = check(_newest(MONDAY, crude=date(2026, 10, 1)), MONDAY)
    assert len(errors) == 1 and "crude" in errors[0]

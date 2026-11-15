"""calculate supports bounded powers, so compound growth is one call (bug: 4000/month for 48 months at 8 %)."""
import pytest

from app import coach, money


def test_compound_growth_in_one_call():
    r = coach.calculate("x", "4000 * ((1 + 0.08/12) ** 48 - 1) / (0.08/12)")
    assert r["result"] == pytest.approx(225399.66, abs=0.05)


@pytest.mark.parametrize("expr", ["10 ** 999", "2 ** 601", "(-8) ** 0.5", "9999999 ** 2"])
def test_powers_are_bounded(expr):
    with pytest.raises(money.ToolError):
        coach.calculate("x", expr)

"""Every "See the payments" list must add up to the number it was opened from, and "largest" must mean largest."""
from app import charts, money

MIKKO = "CUST04588"
S, E = "2026-07-01", "2026-09-30"


def test_largest_really_is_largest():
    tx = money.list_transactions(MIKKO, start=S, end=E, category="Restaurants", sort="largest", limit=5)["transactions"]
    amounts = [t["amount_eur"] for t in tx]
    assert amounts == sorted(amounts, reverse=True) and amounts[0] >= 100


def test_one_offs_largest_first():
    big = money.get_three_baskets(MIKKO, "all")["large_one_offs"]
    amounts = [o["amount_eur"] for o in big]
    assert amounts == sorted(amounts, reverse=True)


def test_payments_match_spending_and_baskets():
    for f in ({}, {"subcategory": "Restaurants"}, {"category": "Restaurants"}, {"basket": 3}):
        sp = money.get_spending(MIKKO, start=S, end=E, **f)
        pay = money.payments(MIKKO, S, E, **f)
        assert (pay["count"], pay["total_eur"]) == (sp["transactions"], sp["total_eur"]), f
    tb = money.get_three_baskets(MIKKO, start=S, end=E)
    for bk in tb["baskets"]:
        pay = money.payments(MIKKO, S, E, basket=bk["basket"])
        assert (pay["count"], pay["total_eur"]) == (bk["transactions"], bk["total_eur"])
        for tp in bk["top"]:
            pay = money.payments(MIKKO, S, E, basket=bk["basket"], subcategory=tp["merchant_type"])
            assert (pay["count"], pay["total_eur"]) == (tp["transactions"], tp["total_eur"])
    cf = money.get_cashflow(MIKKO, start=S, end=E)
    for b, meta in money.BASKETS.items():
        assert money.payments(MIKKO, S, E, basket=b)["total_eur"] == cf["spending_eur"][meta["name"]]


def test_restaurants_category_is_labelled_eating_out():
    assert money.get_spending(MIKKO, start=S, end=E, category="Restaurants")["note"].startswith("Category Restaurants")
    assert charts.show_chart(MIKKO, "category_trend", category="Restaurants")["title"] == "Eating out per month"

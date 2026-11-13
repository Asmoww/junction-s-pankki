"""Fetch Statistics Finland household budget survey 2022 (table 14q4) into app/bench_statfin.json.

Monthly consumption expenditure per consumption unit (EUR, current prices) by age of reference person,
for the COICOP groups we compare against. Open data, CC BY 4.0, Statistics Finland.
Usage: .venv/bin/python scripts/fetch_benchmarks.py
"""
import json
import urllib.request
from pathlib import Path

URL = "https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ktutk/14q4.px"
GROUPS = {"0": "Total", "01": "Food and non-alcoholic beverages", "03": "Clothing and footwear",
          "04": "Housing, water, electricity, gas and other fuels", "05": "Furnishings and household equipment",
          "06": "Health", "07": "Transport", "0732": "Passenger transport by road (incl. taxis, buses)",
          "09": "Recreation, sport and culture", "111": "Food and beverage serving services (restaurants, cafes)"}
AGES = ["SSS", "17-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75-84", "85-"]
query = {"query": [
    {"code": "timeperiod_y", "selection": {"filter": "item", "values": ["2022"]}},
    {"code": "coicop_46_20231201", "selection": {"filter": "item", "values": list(GROUPS)}},
    {"code": "ikaryhma_10_20180101", "selection": {"filter": "item", "values": AGES}},
    {"code": "contentscode", "selection": {"filter": "item", "values": ["kulukk_kt_hk_2_1"]}}],
    "response": {"format": "json-stat2"}}
req = urllib.request.Request(URL, data=json.dumps(query).encode(), headers={"Content-Type": "application/json"})
js = json.load(urllib.request.urlopen(req, timeout=30))
dims = js["id"]
sizes = js["size"]
idx = {d: js["dimension"][d]["category"]["index"] for d in dims}
out = {}
for g in GROUPS:
    for a in AGES:
        pos = {"timeperiod_y": idx["timeperiod_y"]["2022"], "coicop_46_20231201": idx["coicop_46_20231201"][g],
               "ikaryhma_10_20180101": idx["ikaryhma_10_20180101"][a], "contentscode": 0}
        flat = 0
        for d, s in zip(dims, sizes):
            flat = flat * s + pos[d]
        out.setdefault(a, {})[g] = js["value"][flat]
dest = Path(__file__).resolve().parent.parent / "app" / "bench_statfin.json"
dest.write_text(json.dumps({
    "source": "Statistics Finland, Household budget survey 2022, table 14q4 (CC BY 4.0)",
    "url": "https://pxdata.stat.fi/PxWeb/pxweb/en/StatFin/StatFin__ktutk/statfin_ktutk_pxt_14q4.px/",
    "measure": "Consumption expenditure per consumption unit per month, EUR, current prices (2022)",
    "groups": GROUPS, "by_age": out}, indent=1))
print(json.dumps(out["SSS"], indent=0)); print(out["17-24"]["111"], out["25-34"]["111"], out["35-44"]["04"])

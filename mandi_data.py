"""Read a local AGMARKNET extract without making network requests from the website."""

import csv
import os
from datetime import date, datetime
from functools import lru_cache
from math import isfinite
from pathlib import Path
from statistics import median

SOURCE = "https://www.data.gov.in/resource/variety-wise-daily-market-prices-data-commodity"
FIELDS = ("State", "District", "Market", "Commodity", "Variety", "Grade",
          "Arrival_Date", "Modal_Price")
CROPS = {
    "wheat": "wheat", "rice": "rice", "paddy(dhan)(common)": "rice",
    "paddy(dhan)(basmati)": "rice", "paddy(common)": "rice", "paddy(basmati)": "rice",
    "maize": "maize", "barley(jau)": "barley",
    "bengalgram(gram)(whole)": "chickpea", "cotton": "cotton",
    "groundnut": "groundnut", "jowar(sorghum)": "sorghum",
    "bajra(pearlmillet/cumbu)": "pearl_millet", "soyabean": "soybean",
    "soybean": "soybean",
}


def normalized(value):
    return str(value or "").strip().casefold()


def crop_id(commodity):
    return CROPS.get("".join(normalized(commodity).split()))


def data_path():
    directory = Path(os.getenv("CROPNOVA_DATA_DIR") or Path(__file__).parent / "instance")
    return directory / "mandi_prices.csv"


def observation(row):
    try:
        labels = tuple(row[field].strip() for field in FIELDS[:6])
        if not all(labels) or not crop_id(labels[3]):
            return None
        raw_date = row["Arrival_Date"]
        if isinstance(raw_date, date):
            day = raw_date
        else:
            try:
                day = date.fromisoformat(raw_date)
            except ValueError:
                day = datetime.strptime(raw_date, "%d/%m/%Y").date()
        price = float(row["Modal_Price"])
    except (KeyError, ValueError, TypeError, AttributeError):
        return None
    if isfinite(price) and 0 < price <= 1_000_000:
        return labels, day, price
    return None


@lru_cache(maxsize=2)
def read_prices(path, revision):
    groups = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            parsed = observation(row)
            if parsed:
                labels, day, price = parsed
                groups.setdefault(labels, {}).setdefault(day, set()).add(price)
    return {
        labels: tuple((day, median(values)) for day, values in sorted(daily.items()))
        for labels, daily in groups.items()
    }


def comparable_series(region, crop_ids, today):
    path = data_path()
    try:
        info = path.stat()
        groups = read_prices(path, (info.st_mtime_ns, info.st_size))
    except (OSError, UnicodeError, csv.Error):
        return []

    state, district = (normalized(region.get(key)) for key in ("state", "district"))
    if not state:
        return []
    series = []
    for labels, prices in groups.items():
        crop = crop_id(labels[3])
        if normalized(labels[0]) != state or crop not in crop_ids:
            continue
        # Keep every series tied to one mandi, commodity, variety and grade.
        history = tuple((day, price) for day, price in prices if day <= today)
        if history:
            local = bool(district and normalized(labels[1]) == district)
            series.append((labels, crop, history, local))
    return sorted(series, key=lambda item: (
        not item[3], -(item[2][-1][0].toordinal() // 28), -len(item[2]), item[0]
    ))

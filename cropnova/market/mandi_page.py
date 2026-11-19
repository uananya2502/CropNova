"""Show market evidence and apply explicit rules to the saved field finding."""

from datetime import datetime, timedelta
from hashlib import sha256
from html import escape
from zoneinfo import ZoneInfo

from cropnova.market.mandi_data import SOURCE, comparable_series
from cropnova.market.mandi_forecast import assess_forecast

TITLE = {"en": "Mandi prices", "hi": "मंडी भाव", "pa": "ਮੰਡੀ ਭਾਅ"}


def market_guidance(crop, forecast):
    """Field suitability comes first. Price signals never promote an unresolved crop."""
    if crop["status"] == "rejected":
        return "Resolve the recorded field mismatch before considering this crop on price."
    if crop["status"] != "feasible":
        return "Confirm the open field checks before using this price in your shortlist."
    if forecast["state"] != "current":
        return "The crop matches the field checks. Confirm the current quote with the mandi before budgeting."
    change = forecast["price"] - forecast["previous"]
    if abs(change) <= forecast["band"]:
        return "The estimated movement is within past forecast errors. Use the latest quoted price when comparing options."
    direction = "higher" if change > 0 else "lower"
    return (
        f"The crop matches the field checks and the model estimates a {direction} average "
        "for this week. Ask the mandi for a quote for your variety and grade before acting."
    )


def money(price):
    return f"₹{price:,.0f}"


def series_id(labels):
    return sha256(repr(labels).encode()).hexdigest()[:20]


def market_choices(series, crop_ids):
    """Include long histories alongside the newest quotes for each assessed crop."""
    options = {}
    for crop in crop_ids:
        matching = [item for item in series if item[1] == crop]
        longest = sorted(matching, key=lambda item: -len(item[2]))
        local_history = [item for item in longest if item[3]]
        for item in matching[:6] + local_history[:4] + longest[:6]:
            options[series_id(item[0])] = item
    return options


def forecast_details(forecast):
    evaluation = (
        f'<p>{escape(forecast["model"])} on {forecast["test_weeks"]} later test weeks '
        f'({forecast["test_start"]} to {forecast["test_end"]}). Mean absolute error '
        f'was <strong>{money(forecast["error"])}</strong> per quintal, versus '
        f'<strong>{money(forecast["baseline_error"])}</strong> for using the previous week’s average.</p>'
    )
    if forecast["state"] == "baseline_better":
        return (
            "<p>The model did not improve on the baseline by at least 5%. No forecast is available.</p>"
            + evaluation
        )
    if forecast["state"] == "historical":
        return (
            "<p>There are too few recent reports for a current forecast.</p>"
            f'<p>Historical test example for the week of {forecast["replay_date"]}: '
            f'estimated {money(forecast["replay"])}, observed {money(forecast["actual"])} per quintal.</p>'
            + evaluation
        )
    point, band = forecast["price"], forecast["band"]
    end = forecast["target"] + timedelta(days=6)
    return (
        f'<h3>{money(point)} per quintal</h3><p>Estimated average for {forecast["target"]} to {end}.</p>'
        f"<p>Indicative range from past errors: {money(max(0, point-band))} to {money(point+band)}. "
        "The range uses the 80th percentile of errors on the test weeks.</p>" + evaluation
    )


def market_panel(profile, candidates, token, selection=""):
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    crops = {crop["id"]: crop for crop in candidates}
    series = comparable_series(profile.get("region", {}), crops, today)
    coverage_note = ""
    if not series and crops:
        series = comparable_series(profile.get("region", {}), crops, today, other_states=True)
        if series:
            coverage_note = (
                "No imported quote matches these crops in your state. "
                "Showing reported prices for the same crops in other states."
            )
    if not series:
        series = comparable_series(profile.get("region", {}), None, today)
        if series:
            coverage_note = (
                "No imported quote was found for the assessed crops. "
                "Showing other crops in your state for market context."
            )
    if not series:
        return (
            '<section class="panel"><h2>Local price coverage</h2><p>No imported mandi series '
            "matches the assessed crops and state. Check the government source for available quotes.</p>"
            f'<p><a href="{SOURCE}">Open AGMARKNET data ↗</a></p></section>'
        )

    options = market_choices(series, dict.fromkeys(item[1] for item in series))
    default = min(
        options,
        key=lambda key: (
            not options[key][3],
            crops.get(options[key][1], {}).get("status") != "feasible",
        ),
    )
    selected = selection if selection in options else default
    menu = []
    for key, (labels, _, _, _) in options.items():
        state, district, market, commodity, variety, grade = labels
        label = escape(f"{commodity} · {market}, {district}, {state} · {variety} / {grade}")
        active = " selected" if key == selected else ""
        menu.append(f'<option value="{key}"{active}>{label}</option>')
    labels, crop_id, observations, local = options[selected]
    state, district, market, commodity, variety, grade = labels
    latest_day, latest_price = observations[-1]
    forecast = assess_forecast(observations, today)
    crop = crops.get(crop_id)
    forecast_section = ""
    if forecast["state"] != "sparse":
        forecast_section = (
            '<section class="panel"><h2>Weekly price forecast</h2>'
            + forecast_details(forecast)
            + "</section>"
        )
    location_note = (
        "This mandi is in your selected district."
        if local
        else "Check this mandi’s location and travel costs separately."
    )
    guidance = (
        f'<p><strong>{escape(crop["name"])} · {escape(crop["label"])}</strong></p>'
        f'<p>{escape(market_guidance(crop, forecast))}</p>'
        if crop
        else "<p>This crop was not part of your field assessment.</p>"
    )
    coverage = f"<p>{escape(coverage_note)}</p>" if coverage_note else ""
    return f"""
<section class="panel"><h2>Choose a market and variety</h2>
{coverage}<form method="get" action="/assessment/{escape(token, quote=True)}/market">
<div class="field">
<label for="mandi-series">Reported mandi series</label>
<select id="mandi-series" name="series">{''.join(menu)}</select></div>
<p><button type="submit" class="button">Show prices</button></p></form></section>
<section class="panel"><h2>{escape(commodity)} at {escape(market)}</h2>
<p>{escape(district)}, {escape(state)} · {escape(variety)} / {escape(grade)}. {location_note}</p>
<h3>{money(latest_price)} per quintal</h3><p>Reported {latest_day:%d %B %Y}</p></section>
{forecast_section}
<section class="panel"><h2>How to use this with your field assessment</h2>
{guidance}
<p>Use these wholesale prices as market context. Your sale price depends on the quote and the produce you bring.</p>
<p><a href="{SOURCE}">Source: AGMARKNET via India’s Open Government Data Platform ↗</a></p></section>"""

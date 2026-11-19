"""Forecast weekly wholesale prices using only observations available before each week."""

from datetime import timedelta
from math import ceil
from statistics import mean

WEEK = timedelta(days=7)
BASELINE = "Previous week’s average"
MODELS = ("Recent trend regression", "Three-week trend regression")


def week_start(day):
    return day - timedelta(days=day.weekday())


def weekly_prices(observations, as_of):
    """Average the reported daily modal prices in completed, adequately reported weeks."""
    weeks = {}
    for day, price in observations:
        week = week_start(day)
        if week < week_start(as_of):
            weeks.setdefault(week, []).append(price)
    return {week: mean(prices) for week, prices in weeks.items() if len(prices) >= 3}


def model_inputs(weeks, target):
    """Predict a change from last week using the preceding three complete weeks."""
    prior = [weeks.get(target - n * WEEK) for n in (1, 2, 3)]
    if None in prior:
        return None
    last, previous, older = prior
    return last, (last - previous, last - mean([previous, older]))


def training_rows(weeks):
    rows = []
    for target in sorted(weeks):
        features = model_inputs(weeks, target)
        if features:
            last, trends = features
            rows.append((target, last, trends, weeks[target]))
    return rows


def train(rows, feature):
    """Fit one linear trend with shrinkage toward the no-change baseline."""
    x = [row[2][feature] for row in rows]
    y = [row[3] - row[1] for row in rows]
    x_mean, y_mean = mean(x), mean(y)
    variance = sum((value - x_mean) ** 2 for value in x)
    covariance = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y))
    slope = covariance / (variance * (1 + 10 / len(rows))) if variance else 0
    return y_mean - slope * x_mean, slope


def predict(last, trends, feature, coefficients):
    intercept, slope = coefficients
    return max(0, last + intercept + slope * trends[feature])


def evaluate(rows, feature, coefficients):
    return [
        abs(actual - predict(last, trends, feature, coefficients))
        for _, last, trends, actual in rows
    ]


def assess_forecast(observations, as_of):
    """Choose on validation weeks, gate on a separate test block, then refit."""
    weeks = weekly_prices(observations, as_of)
    rows = training_rows(weeks)
    if len(rows) < 40:
        return {"state": "sparse", "weeks": len(rows)}

    test_size = max(10, len(rows) // 5)
    validation_size = max(8, len(rows) // 5)
    train_rows = rows[: -(test_size + validation_size)]
    validation = rows[-(test_size + validation_size) : -test_size]
    test = rows[-test_size:]
    feature = min(
        range(len(MODELS)),
        key=lambda index: mean(evaluate(validation, index, train(train_rows, index))),
    )
    coefficients = train(rows[:-test_size], feature)
    errors = evaluate(test, feature, coefficients)
    baseline_error = mean(abs(actual - last) for _, last, _, actual in test)
    error = mean(errors)
    result = {
        "state": "baseline_better",
        "model": MODELS[feature],
        "baseline": BASELINE,
        "error": error,
        "baseline_error": baseline_error,
        "test_weeks": len(test),
        "test_start": test[0][0],
        "test_end": test[-1][0] + 6 * timedelta(days=1),
    }
    if baseline_error == 0 or error >= baseline_error * 0.95:
        return result

    band = sorted(errors)[ceil(len(errors) * 0.8) - 1]
    day, last, trends, actual = test[-1]
    result.update(
        state="historical",
        band=band,
        replay_date=day,
        replay=predict(last, trends, feature, coefficients),
        actual=actual,
    )
    target = week_start(as_of)
    features = model_inputs(weeks, target)
    # A forecast is for the current calendar week, using data through last Sunday.
    if features and (as_of - observations[-1][0]).days <= 7:
        last, trends = features
        result.update(
            state="current",
            target=target,
            previous=last,
            price=predict(last, trends, feature, train(rows, feature)),
        )
    return result

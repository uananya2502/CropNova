"""Small, predictable language helpers; crop decisions stay in the existing engine."""

LANGUAGES = {"en": "English", "hi": "हिंदी", "pa": "ਪੰਜਾਬੀ"}
RAIN_CHOICES = [
    ("none", "No Rain", "The field has had no useful rain."),
    ("low", "Low Rain", "A little rain; the soil dries quickly."),
    ("medium", "Medium Rain", "Some regular rain; the soil stays moist for a while."),
    ("high", "High Rain", "Frequent heavy rain; watch for standing water."),
]
RAIN_LABELS = {key: label for key, label, _ in RAIN_CHOICES}


def language_settings(profile):
    language = profile.get("language", "en")
    language = language if language in LANGUAGES else "en"
    return language, ["en", "hi", "pa"] if profile.get("multilingual_view") == "yes" else [language]


def rain_icon(kind):
    """Decorative inline drawings work offline and do not rely on an icon font."""
    sun = '<circle cx="30" cy="24" r="10" fill="#e8b34c"/><path d="M30 6v5M30 37v5M12 24h5M43 24h5M17 11l4 4M40 34l4 4M17 37l4-4M40 14l4-4" stroke="#bf8735"/>'
    cloud = '<path d="M17 30C5 29 7 15 17 15c4-13 23-11 25 2 13-1 14 17 2 18H18" fill="#e0e8db" stroke="#5a785e"/>'
    drops = {
        "none": "",
        "low": "M26 39l-2 5M39 40l-2 5",
        "medium": "M20 39l-3 7M31 40l-3 7M43 39l-3 7",
        "high": "M17 39l-4 9M28 40l-4 9M40 39l-4 9M49 42l-3 7",
    }
    drawing = (
        sun
        if kind == "none"
        else cloud + f'<path d="{drops[kind]}" stroke="#4c785b" stroke-width="3"/>'
    )
    return (
        '<svg viewBox="0 0 64 56" fill="none" stroke-linecap="round" aria-hidden="true">'
        + drawing
        + "</svg>"
    )


def rainfall_fields(values):
    from html import escape

    choices = []
    for key, label, description in RAIN_CHOICES:
        checked = " checked" if values.get("rainfall_level") == key else ""
        choices.append(
            f'<label class="rain-choice"><input type="radio" name="rainfall_level" value="{key}"{checked}><span class="rain-choice-content">{rain_icon(key)}<strong>{label}</strong><small>{description}</small></span></label>'
        )
    exact = escape(str(values.get("rainfall_mm", "")), quote=True)
    return (
        '<fieldset class="rainfall-fieldset"><legend>How much rain has your field received this growing season?</legend><p>Choose what you have observed. You can leave this unanswered if you are unsure.</p><div class="rain-choice-grid">'
        + "".join(choices)
        + f'</div><details class="rainfall-advanced"><summary>I know the exact rainfall (optional)</summary><label for="rainfall_mm">Measured rainfall this season, in millimetres</label><input type="number" id="rainfall_mm" name="rainfall_mm" min="0" max="10000" step="0.1" inputmode="decimal" value="{exact}" placeholder="For example, 350"><small>Use a rain gauge or local measurement. Rainfall is recorded separately from usable water for the crop.</small></details><p class="small">Rain descriptions have no fixed millimetre value. They are not a rainfall forecast or a substitute for a crop-water estimate.</p></fieldset>'
    )


NAMES = {
    "hi": ["बुवाई का मौसम", "पानी", "मिट्टी", "मिट्टी का pH"],
    "pa": ["ਬਿਜਾਈ ਦਾ ਮੌਸਮ", "ਪਾਣੀ", "ਮਿੱਟੀ", "ਮਿੱਟੀ ਦਾ pH"],
}
CROPS = {
    "hi": dict(
        wheat="गेहूँ",
        rice="धान",
        maize="मक्का",
        chickpea="चना",
        barley="जौ",
        cotton="कपास",
        groundnut="मूँगफली",
        sorghum="ज्वार",
        pearl_millet="बाजरा",
        soybean="सोयाबीन",
    ),
    "pa": dict(
        wheat="ਕਣਕ",
        rice="ਝੋਨਾ",
        maize="ਮੱਕੀ",
        chickpea="ਛੋਲੇ",
        barley="ਜੌਂ",
        cotton="ਨਰਮਾ / ਕਪਾਹ",
        groundnut="ਮੂੰਗਫਲੀ",
        sorghum="ਜੁਆਰ",
        pearl_millet="ਬਾਜਰਾ",
        soybean="ਸੋਇਆਬੀਨ",
    ),
}


def native_value(value, language):
    translations = {
        "hi": {
            "Not provided": "नहीं बताया",
            "No applicable published reference": "इस जगह का प्रकाशित संदर्भ उपलब्ध नहीं है",
            "Not compared until this detail is provided": "यह जानकारी मिलने पर जाँच होगी",
            "Rabi": "रबी",
            "Kharif": "खरीफ",
            "Zaid": "जायद",
            "Loamy": "दोमट",
            "Sandy loam": "बलुई दोमट",
            "Clay loam": "चिकनी दोमट",
            "Clayey": "चिकनी मिट्टी",
            "Sandy": "रेतीली",
            "preferred pH": "पसंदीदा pH",
            "seasonal crop-water use": "पूरे फसल मौसम में पानी का उपयोग",
            "supplemental irrigation": "अतिरिक्त सिंचाई",
            "mm": "मिमी",
        },
        "pa": {
            "Not provided": "ਨਹੀਂ ਦੱਸਿਆ",
            "No applicable published reference": "ਇਸ ਥਾਂ ਦਾ ਪ੍ਰਕਾਸ਼ਿਤ ਹਵਾਲਾ ਉਪਲਬਧ ਨਹੀਂ",
            "Not compared until this detail is provided": "ਇਹ ਜਾਣਕਾਰੀ ਮਿਲਣ ਉੱਤੇ ਜਾਂਚ ਹੋਵੇਗੀ",
            "Rabi": "ਹਾੜ੍ਹੀ",
            "Kharif": "ਸਾਉਣੀ",
            "Zaid": "ਗਰਮੀ ਦੀ ਫ਼ਸਲ",
            "Loamy": "ਦੋਮਟ",
            "Sandy loam": "ਰੇਤਲੀ ਦੋਮਟ",
            "Clay loam": "ਚੀਕਣੀ ਦੋਮਟ",
            "Clayey": "ਚੀਕਣੀ ਮਿੱਟੀ",
            "Sandy": "ਰੇਤਲੀ",
            "preferred pH": "ਪਸੰਦੀਦਾ pH",
            "seasonal crop-water use": "ਪੂਰੇ ਫ਼ਸਲ ਮੌਸਮ ਵਿੱਚ ਪਾਣੀ ਦੀ ਵਰਤੋਂ",
            "supplemental irrigation": "ਵਾਧੂ ਸਿੰਚਾਈ",
            "mm": "ਮਿ.ਮੀ.",
        },
    }
    for original, translated in translations.get(language, {}).items():
        value = value.replace(original, translated)
    return value

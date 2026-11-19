"""Evidence-based farmer wording, available even when the LLM is unavailable."""

from html import escape
import re
from cropnova.web.farmer_language import LANGUAGES, language_settings, NAMES, CROPS, native_value

WORDS = {
    "en": dict(
        title="What this means for your field",
        match="matches the reference",
        open="still needs checking",
        failed="needs attention",
        chosen="This crop matches the four conditions we checked.",
        review="Check the following points before choosing this crop.",
        water="Water for this crop",
        precaution="Before you sow",
        caution="Confirm the crop variety, local water needs and sowing time with your local agricultural adviser. This comparison cannot guarantee a harvest.",
    ),
    "hi": dict(
        title="आपके खेत के लिए इसका मतलब",
        match="दी गई जानकारी से मेल खाता है",
        open="की जाँच अभी बाकी है",
        failed="पर ध्यान देना जरूरी है",
        chosen="यह फसल जाँची गई चारों बातों से मेल खाती है।",
        review="इस फसल को चुनने से पहले नीचे दी गई बातें जाँच लें।",
        water="इस फसल के लिए पानी",
        precaution="बुवाई से पहले",
        caution="स्थानीय कृषि सलाहकार से किस्म, पानी की जरूरत और बुवाई का समय पक्का करें। यह तुलना अच्छी पैदावार की गारंटी नहीं है।",
    ),
    "pa": dict(
        title="ਤੁਹਾਡੇ ਖੇਤ ਲਈ ਇਸ ਦਾ ਮਤਲਬ",
        match="ਦਿੱਤੀ ਜਾਣਕਾਰੀ ਨਾਲ ਮੇਲ ਖਾਂਦਾ ਹੈ",
        open="ਦੀ ਜਾਂਚ ਅਜੇ ਬਾਕੀ ਹੈ",
        failed="ਵੱਲ ਧਿਆਨ ਦੇਣ ਦੀ ਲੋੜ ਹੈ",
        chosen="ਇਹ ਫ਼ਸਲ ਜਾਂਚੀਆਂ ਚਾਰਾਂ ਗੱਲਾਂ ਨਾਲ ਮੇਲ ਖਾਂਦੀ ਹੈ।",
        review="ਇਹ ਫ਼ਸਲ ਚੁਣਨ ਤੋਂ ਪਹਿਲਾਂ ਹੇਠਾਂ ਦਿੱਤੀਆਂ ਗੱਲਾਂ ਦੀ ਜਾਂਚ ਕਰੋ।",
        water="ਇਸ ਫ਼ਸਲ ਲਈ ਪਾਣੀ",
        precaution="ਬਿਜਾਈ ਤੋਂ ਪਹਿਲਾਂ",
        caution="ਸਥਾਨਕ ਖੇਤੀ ਸਲਾਹਕਾਰ ਤੋਂ ਕਿਸਮ, ਪਾਣੀ ਦੀ ਲੋੜ ਅਤੇ ਬਿਜਾਈ ਦਾ ਸਮਾਂ ਪੱਕਾ ਕਰੋ। ਇਹ ਤੁਲਨਾ ਚੰਗੇ ਝਾੜ ਦੀ ਗਾਰੰਟੀ ਨਹੀਂ ਹੈ।",
    ),
}


def specific_precautions(crop, language):
    """Prioritise unresolved measured conditions; never prescribe a treatment."""
    actions = []
    for index, check in enumerate(crop["checks"]):
        if check["status"] == "satisfied":
            continue
        native = {
            "hi": [
                "अपने इलाके में इस फसल की बुवाई का मौसम पक्का करें।",
                "इस फसल के पूरे मौसम के लिए उपलब्ध पानी का भरोसेमंद अनुमान लें। बारिश का अंदाजा अपने आप सिंचाई का पानी नहीं बताता।",
                "मिट्टी का प्रकार और खेत से पानी निकलने की स्थिति पक्का करें।",
                "मिट्टी की जाँच रिपोर्ट से pH पक्का करें और स्थानीय कृषि सलाहकार से तुलना समझें।",
            ],
            "pa": [
                "ਆਪਣੇ ਇਲਾਕੇ ਵਿੱਚ ਇਸ ਫ਼ਸਲ ਦੀ ਬਿਜਾਈ ਦਾ ਮੌਸਮ ਪੱਕਾ ਕਰੋ।",
                "ਪੂਰੇ ਫ਼ਸਲ ਮੌਸਮ ਲਈ ਵਰਤਣਯੋਗ ਪਾਣੀ ਦਾ ਭਰੋਸੇਯੋਗ ਅੰਦਾਜ਼ਾ ਲਵੋ। ਮੀਂਹ ਦਾ ਅੰਦਾਜ਼ਾ ਆਪਣੇ ਆਪ ਸਿੰਚਾਈ ਦਾ ਪਾਣੀ ਨਹੀਂ ਦੱਸਦਾ।",
                "ਮਿੱਟੀ ਦੀ ਕਿਸਮ ਅਤੇ ਖੇਤ ਵਿੱਚੋਂ ਪਾਣੀ ਨਿਕਲਣ ਦੀ ਹਾਲਤ ਪੱਕੀ ਕਰੋ।",
                "ਮਿੱਟੀ ਦੀ ਜਾਂਚ ਰਿਪੋਰਟ ਤੋਂ pH ਪੱਕਾ ਕਰੋ ਅਤੇ ਸਥਾਨਕ ਖੇਤੀ ਸਲਾਹਕਾਰ ਤੋਂ ਤੁਲਨਾ ਸਮਝੋ।",
            ],
        }
        actions.append(native[language][index] if language in native else check["reason"])
    return actions[:2]


def farmer_block(crop, language):
    words = WORDS[language]
    name = CROPS.get(language, {}).get(crop["id"], crop["name"])
    lead = words["chosen"] if crop["status"] == "feasible" else words["review"]
    from cropnova.web.farmer_narrative import check_detail

    lines = []
    reference_label = {"en": "Crop guide", "hi": "फसल का संदर्भ", "pa": "ਫ਼ਸਲ ਦਾ ਹਵਾਲਾ"}[language]
    for i, check in enumerate(crop["checks"]):
        label = NAMES.get(language, [c["name"] for c in crop["checks"]])[i]
        state = words[
            {"satisfied": "match", "unknown": "open", "violated": "failed"}[check["status"]]
        ]
        symbol = {"satisfied": "✓", "unknown": "?", "violated": "!"}[check["status"]]
        entered = native_value(check["entered"], language)
        reference = native_value(check["reference"], language)
        # Matched checks show the value and reference once. Keep the full reason
        # for unresolved English checks so shortening never hides a qualification.
        interpretation, implication = check_detail(check, i, language)
        reason = (
            '<div class="check-detailed-explanation"><p>'
            + escape(interpretation)
            + "</p><p>"
            + escape(implication)
            + "</p></div>"
        )
        lines.append(
            f'<li class="farmer-check {check["status"]}"><div class="farmer-check-heading"><strong>{escape(label)}</strong><span class="check-indicator" role="img" aria-label="{escape(state,quote=True)}">{symbol}</span></div><span class="farmer-check-value">{escape(entered)}</span><p class="farmer-check-reference">{reference_label}: {escape(reference)}</p>{reason}</li>'
        )
    precautions = "".join(
        "<p>" + escape(action) + "</p>" for action in specific_precautions(crop, language)
    )
    from cropnova.web.web_views import crop_icon

    return f'<article class="farmer-language-block" lang="{language}"><header class="language-card-header"><span class="language-label">{LANGUAGES[language]}</span><div class="language-card-crop"><span class="language-crop-icon">{crop_icon(crop["id"])}</span><h3>{escape(name)}</h3></div></header><div class="language-card-body"><p class="language-card-lead">{escape(lead)}</p><ul class="farmer-checks">{"".join(lines)}</ul><aside class="language-card-precaution"><h4>{words["precaution"]}</h4>{precautions}<p>{words["caution"]}</p></aside></div></article>'


def farmer_explanation_panel(report, summary):
    language, languages = language_settings(report.get("profile", {}))
    # Focus the first view on supported options; retain all detailed findings below.
    crops = [c for c in summary["candidates"] if c["status"] == "feasible"] or summary[
        "candidates"
    ][:1]
    panels = "".join(
        '<div class="language-columns">'
        + "".join(farmer_block(c, lang) for lang in languages)
        + "</div>"
        for c in crops
    )
    return f'<section class="panel farmer-explanations" id="field-explanation"><span class="eyebrow">Your field, explained simply</span><h2>{WORDS[language]["title"]}</h2>{panels}<p class="small">These explanations use the recorded crop checks. Open the crop findings for original references.</p></section>'


def prose_paragraphs(text):
    """Preserve the writer's short paragraphs while escaping every character."""
    return "".join(
        "<p>" + escape(part.strip()) + "</p>" for part in re.split(r"\n\s*\n", text) if part.strip()
    )


def generated_language_text(row):
    """Only escaped, validated provider text is displayed as generated language."""
    translations = row.get("translations")
    if not translations:
        return prose_paragraphs(row["text"])
    return (
        '<div class="language-columns">'
        + "".join(
            f'<article class="farmer-language-block generated-language-block" lang="{escape(t["language"],quote=True)}"><header class="language-card-header"><span class="language-label">{LANGUAGES.get(t["language"],t["language"])}</span></header><div class="language-card-body">{prose_paragraphs(t["text"])}<aside class="language-card-precaution"><h4>{WORDS.get(t["language"], WORDS["en"])["precaution"]}</h4><p>{escape(t.get("precaution", ""))}</p></aside></div></article>'
            for t in translations
        )
        + "</div>"
    )

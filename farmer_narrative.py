"""Detailed, deterministic explanations in the farmer's selected language.

This module interprets recorded checks. It does not predict a new result or add
agronomic requirements. The LLM is optional; these explanations work offline.
"""
from farmer_language import native_value, CROPS, NAMES

LABELS = {
 'en':dict(plan='Your next steps', plan_title='A practical order for following up', focus='Focus', plan_intro='Resolve the open checks first, then confirm local sowing and water arrangements before choosing seed.', why='Why this step matters for your field', entered='Your entry', reference='Crop guide', no_source='No applicable published reference was recorded. Obtain local guidance before using this as a crop recommendation.', report='Your personalised report', overview='What the assessment tells you', comparison='Comparison of assessed crops', detailed='Detailed crop findings', meaning='What this means', practical='What to do with this result', published='Published planning guidance', boundaries='What this report cannot establish', input_record='Your recorded field details', actions='Your action checklist', sources='Sources used in this assessment', match='Matches checked conditions', unknown='Needs more information', rejected='Needs attention', checked='conditions matched', ai='Additional AI explanation', ai_note='AI connects the recorded findings into a fuller explanation. It does not independently verify the farm or change the crop result.', missing='What still needs checking?', new='New assessment', edit='Update field details', edit_title='Ready to update a measurement?', edit_body='Add the information you have confirmed and create a new assessment. Your saved findings remain unchanged.', view='View crop findings', report_link='Read my report', guide='Published reference; confirm current local guidance.'),
 'hi':dict(plan='आपके अगले कदम', plan_title='अब क्या करें और किस क्रम में करें', focus='इन फसलों पर ध्यान दें', plan_intro='पहले अधूरी जाँच पूरी करें। बीज चुनने से पहले स्थानीय बुवाई के समय और पानी की व्यवस्था पक्की करें।', why='आपके खेत के लिए यह कदम क्यों जरूरी है', entered='आपकी जानकारी', reference='फसल का संदर्भ', no_source='इस जाँच के लिए लागू प्रकाशित संदर्भ दर्ज नहीं है। फसल चुनने से पहले स्थानीय कृषि सलाह लें।', report='आपकी व्यक्तिगत खेत रिपोर्ट', overview='इस आकलन से क्या पता चलता है', comparison='जाँची गई फसलों की तुलना', detailed='फसल की विस्तृत जाँच', meaning='इसका मतलब', practical='इस नतीजे के आधार पर क्या करें', published='प्रकाशित बुवाई और अवधि की जानकारी', boundaries='इस रिपोर्ट से क्या पक्का नहीं होता', input_record='आपके खेत की दर्ज जानकारी', actions='आपके कामों की सूची', sources='इस आकलन में इस्तेमाल किए गए स्रोत', match='जाँची गई बातें मेल खाती हैं', unknown='और जानकारी चाहिए', rejected='ध्यान देने की जरूरत है', checked='बातें मेल खाती हैं', ai='अतिरिक्त AI व्याख्या', ai_note='AI दर्ज जाँचों को जोड़कर समझाता है। यह खेत की स्वतंत्र जाँच नहीं करता और फसल का नतीजा नहीं बदलता।', missing='क्या जाँचना अभी बाकी है?', new='नया आकलन', edit='खेत की जानकारी बदलें', edit_title='कोई जानकारी पक्की हो गई है?', edit_body='पक्की जानकारी भरकर नया आकलन करें। पुराना नतीजा अपने आप नहीं बदलेगा।', view='फसल के नतीजे देखें', report_link='मेरी रिपोर्ट पढ़ें', guide='यह प्रकाशित संदर्भ है; मौजूदा स्थानीय सलाह पक्की करें।'),
 'pa':dict(plan='ਤੁਹਾਡੇ ਅਗਲੇ ਕਦਮ', plan_title='ਹੁਣ ਕੀ ਕਰਨਾ ਹੈ ਅਤੇ ਕਿਸ ਕ੍ਰਮ ਵਿੱਚ', focus='ਇਨ੍ਹਾਂ ਫ਼ਸਲਾਂ ਉੱਤੇ ਧਿਆਨ ਦਿਓ', plan_intro='ਪਹਿਲਾਂ ਅਧੂਰੀ ਜਾਂਚ ਪੂਰੀ ਕਰੋ। ਬੀਜ ਚੁਣਨ ਤੋਂ ਪਹਿਲਾਂ ਸਥਾਨਕ ਬਿਜਾਈ ਦਾ ਸਮਾਂ ਅਤੇ ਪਾਣੀ ਦਾ ਪ੍ਰਬੰਧ ਪੱਕਾ ਕਰੋ।', why='ਤੁਹਾਡੇ ਖੇਤ ਲਈ ਇਹ ਕਦਮ ਕਿਉਂ ਜ਼ਰੂਰੀ ਹੈ', entered='ਤੁਹਾਡੀ ਜਾਣਕਾਰੀ', reference='ਫ਼ਸਲ ਦਾ ਹਵਾਲਾ', no_source='ਇਸ ਜਾਂਚ ਲਈ ਲਾਗੂ ਪ੍ਰਕਾਸ਼ਿਤ ਹਵਾਲਾ ਦਰਜ ਨਹੀਂ ਹੈ। ਫ਼ਸਲ ਚੁਣਨ ਤੋਂ ਪਹਿਲਾਂ ਸਥਾਨਕ ਖੇਤੀ ਸਲਾਹ ਲਵੋ।', report='ਤੁਹਾਡੀ ਨਿੱਜੀ ਖੇਤ ਰਿਪੋਰਟ', overview='ਇਸ ਮੁਲਾਂਕਣ ਤੋਂ ਕੀ ਪਤਾ ਲੱਗਦਾ ਹੈ', comparison='ਜਾਂਚੀਆਂ ਫ਼ਸਲਾਂ ਦੀ ਤੁਲਨਾ', detailed='ਫ਼ਸਲ ਦੀ ਵਿਸਥਾਰ ਨਾਲ ਜਾਂਚ', meaning='ਇਸ ਦਾ ਮਤਲਬ', practical='ਇਸ ਨਤੀਜੇ ਦੇ ਆਧਾਰ ਉੱਤੇ ਕੀ ਕਰੋ', published='ਪ੍ਰਕਾਸ਼ਿਤ ਬਿਜਾਈ ਅਤੇ ਮਿਆਦ ਦੀ ਜਾਣਕਾਰੀ', boundaries='ਇਸ ਰਿਪੋਰਟ ਤੋਂ ਕੀ ਪੱਕਾ ਨਹੀਂ ਹੁੰਦਾ', input_record='ਤੁਹਾਡੇ ਖੇਤ ਦੀ ਦਰਜ ਜਾਣਕਾਰੀ', actions='ਤੁਹਾਡੇ ਕੰਮਾਂ ਦੀ ਸੂਚੀ', sources='ਇਸ ਮੁਲਾਂਕਣ ਵਿੱਚ ਵਰਤੇ ਸਰੋਤ', match='ਜਾਂਚੀਆਂ ਗੱਲਾਂ ਮੇਲ ਖਾਂਦੀਆਂ ਹਨ', unknown='ਹੋਰ ਜਾਣਕਾਰੀ ਚਾਹੀਦੀ ਹੈ', rejected='ਧਿਆਨ ਦੇਣ ਦੀ ਲੋੜ ਹੈ', checked='ਗੱਲਾਂ ਮੇਲ ਖਾਂਦੀਆਂ ਹਨ', ai='ਵਾਧੂ AI ਵਿਆਖਿਆ', ai_note='AI ਦਰਜ ਜਾਂਚਾਂ ਨੂੰ ਜੋੜ ਕੇ ਸਮਝਾਉਂਦਾ ਹੈ। ਇਹ ਖੇਤ ਦੀ ਸੁਤੰਤਰ ਜਾਂਚ ਨਹੀਂ ਕਰਦਾ ਅਤੇ ਫ਼ਸਲ ਦਾ ਨਤੀਜਾ ਨਹੀਂ ਬਦਲਦਾ।', missing='ਕੀ ਜਾਂਚਣਾ ਅਜੇ ਬਾਕੀ ਹੈ?', new='ਨਵਾਂ ਮੁਲਾਂਕਣ', edit='ਖੇਤ ਦੀ ਜਾਣਕਾਰੀ ਬਦਲੋ', edit_title='ਕੋਈ ਜਾਣਕਾਰੀ ਪੱਕੀ ਹੋ ਗਈ ਹੈ?', edit_body='ਪੱਕੀ ਜਾਣਕਾਰੀ ਭਰ ਕੇ ਨਵਾਂ ਮੁਲਾਂਕਣ ਕਰੋ। ਪੁਰਾਣਾ ਨਤੀਜਾ ਆਪਣੇ ਆਪ ਨਹੀਂ ਬਦਲੇਗਾ।', view='ਫ਼ਸਲਾਂ ਦੇ ਨਤੀਜੇ ਵੇਖੋ', report_link='ਮੇਰੀ ਰਿਪੋਰਟ ਪੜ੍ਹੋ', guide='ਇਹ ਪ੍ਰਕਾਸ਼ਿਤ ਹਵਾਲਾ ਹੈ; ਮੌਜੂਦਾ ਸਥਾਨਕ ਸਲਾਹ ਪੱਕੀ ਕਰੋ।'),
}

# Practical implications explain the limits of each implemented measurement.
IMPLICATIONS = {
 'en':[
  'A season match is useful for shortlisting, but it does not choose an exact sowing date or a variety. Confirm the current local sowing window and seed variety before planting.',
  'This compares the amount over the crop season, not the volume to apply in one irrigation. Useful rainfall, stored soil moisture, irrigation reliability and timing must be considered locally. A rain category alone cannot supply this measurement.',
  'This check compares soil texture; it does not test soil fertility, salinity, compaction or every drainage condition. Confirm the texture and any drainage requirement from the reference before using this result for field planning.',
  'This is a preferred pH range, not a boundary beyond which the crop cannot grow. A matching pH does not establish nutrient levels or a fertiliser dose. Use a measured soil report and seek local advice about any result outside the preferred range.'
 ],
 'hi':[
  'मौसम का मेल फसल की शुरुआती सूची बनाने में मदद करता है। इससे बुवाई की सही तारीख या किस्म अपने आप तय नहीं होती। बोने से पहले अपने इलाके की मौजूदा बुवाई अवधि और बीज की किस्म पक्की करें।',
  'यह पूरे फसल मौसम के पानी की तुलना है, एक बार की सिंचाई में देने की मात्रा नहीं। उपयोगी बारिश, मिट्टी में मौजूद नमी, सिंचाई की उपलब्धता और पानी मिलने का समय स्थानीय तौर पर जाँचें। केवल कम या ज्यादा बारिश चुनने से यह मात्रा तय नहीं होती।',
  'यह जाँच केवल मिट्टी की बनावट की तुलना करती है। इससे उपजाऊपन, लवणता, दबाव से सख्त मिट्टी या पानी निकलने की हर स्थिति नहीं जाँची जाती। खेत की योजना बनाने से पहले मिट्टी का प्रकार और संदर्भ में दी गई जल निकासी की जरूरत पक्की करें।',
  'यह पसंदीदा pH सीमा है; इसके बाहर फसल कभी नहीं उग सकती, ऐसा मतलब नहीं है। pH मेल खाने से पोषक तत्व या खाद की मात्रा तय नहीं होती। मापी गई मिट्टी-जाँच रिपोर्ट इस्तेमाल करें और सीमा से बाहर नतीजे पर स्थानीय सलाह लें।'
 ],
 'pa':[
  'ਮੌਸਮ ਦਾ ਮੇਲ ਫ਼ਸਲ ਦੀ ਸ਼ੁਰੂਆਤੀ ਸੂਚੀ ਬਣਾਉਣ ਵਿੱਚ ਮਦਦ ਕਰਦਾ ਹੈ। ਇਸ ਨਾਲ ਬਿਜਾਈ ਦੀ ਸਹੀ ਤਾਰੀਖ ਜਾਂ ਕਿਸਮ ਆਪਣੇ ਆਪ ਤੈਅ ਨਹੀਂ ਹੁੰਦੀ। ਬੀਜਣ ਤੋਂ ਪਹਿਲਾਂ ਆਪਣੇ ਇਲਾਕੇ ਦੀ ਮੌਜੂਦਾ ਬਿਜਾਈ ਮਿਆਦ ਅਤੇ ਬੀਜ ਦੀ ਕਿਸਮ ਪੱਕੀ ਕਰੋ।',
  'ਇਹ ਪੂਰੇ ਫ਼ਸਲ ਮੌਸਮ ਦੇ ਪਾਣੀ ਦੀ ਤੁਲਨਾ ਹੈ, ਇੱਕ ਵਾਰ ਦੀ ਸਿੰਚਾਈ ਵਿੱਚ ਦੇਣ ਦੀ ਮਾਤਰਾ ਨਹੀਂ। ਲਾਭਕਾਰੀ ਮੀਂਹ, ਮਿੱਟੀ ਦੀ ਨਮੀ, ਸਿੰਚਾਈ ਦੀ ਉਪਲਬਧਤਾ ਅਤੇ ਪਾਣੀ ਮਿਲਣ ਦਾ ਸਮਾਂ ਸਥਾਨਕ ਤੌਰ ਉੱਤੇ ਜਾਂਚੋ। ਸਿਰਫ਼ ਘੱਟ ਜਾਂ ਵੱਧ ਮੀਂਹ ਚੁਣਨ ਨਾਲ ਇਹ ਮਾਤਰਾ ਤੈਅ ਨਹੀਂ ਹੁੰਦੀ।',
  'ਇਹ ਜਾਂਚ ਸਿਰਫ਼ ਮਿੱਟੀ ਦੀ ਬਣਤਰ ਦੀ ਤੁਲਨਾ ਕਰਦੀ ਹੈ। ਇਸ ਨਾਲ ਉਪਜਾਊਪਣ, ਖਾਰਾਪਣ, ਦੱਬੀ ਹੋਈ ਮਿੱਟੀ ਜਾਂ ਪਾਣੀ ਨਿਕਲਣ ਦੀ ਹਰ ਹਾਲਤ ਨਹੀਂ ਜਾਂਚੀ ਜਾਂਦੀ। ਖੇਤ ਦੀ ਯੋਜਨਾ ਤੋਂ ਪਹਿਲਾਂ ਮਿੱਟੀ ਦੀ ਕਿਸਮ ਅਤੇ ਹਵਾਲੇ ਵਿੱਚ ਦਿੱਤੀ ਨਿਕਾਸੀ ਦੀ ਲੋੜ ਪੱਕੀ ਕਰੋ।',
  'ਇਹ ਪਸੰਦੀਦਾ pH ਹੱਦ ਹੈ; ਇਸ ਤੋਂ ਬਾਹਰ ਫ਼ਸਲ ਕਦੇ ਨਹੀਂ ਉੱਗ ਸਕਦੀ, ਅਜਿਹਾ ਮਤਲਬ ਨਹੀਂ। pH ਮੇਲ ਖਾਣ ਨਾਲ ਪੋਸ਼ਕ ਤੱਤ ਜਾਂ ਖਾਦ ਦੀ ਮਾਤਰਾ ਤੈਅ ਨਹੀਂ ਹੁੰਦੀ। ਮਾਪੀ ਹੋਈ ਮਿੱਟੀ-ਜਾਂਚ ਰਿਪੋਰਟ ਵਰਤੋ ਅਤੇ ਹੱਦ ਤੋਂ ਬਾਹਰ ਨਤੀਜੇ ਉੱਤੇ ਸਥਾਨਕ ਸਲਾਹ ਲਵੋ।'
 ],
}


def crop_name(crop, language):
    return CROPS.get(language, {}).get(crop['id'], crop['name'])


def check_detail(check, index, language):
    if language == 'en':
        return check['reason'], IMPLICATIONS[language][index]
    entered = native_value(check['entered'], language)
    reference = native_value(check['reference'], language)
    code = check.get('reason_code', '')
    if language == 'hi':
        if code == 'MISSING_USER_INPUT': text='इस जाँच के लिए जरूरी माप या खेत की जानकारी नहीं दी गई है। इसे मेल खाने वाला नतीजा नहीं माना गया है।'
        elif code == 'MISSING_VERIFIED_FACT': text='इस फसल और जगह के लिए लागू प्रकाशित संदर्भ अभी उपलब्ध नहीं है। इसका मतलब यह नहीं कि फसल अनुपयुक्त है; स्थानीय जानकारी चाहिए।'
        elif code == 'OUTSIDE_PREFERRED_RANGE': text=f'आपका pH {entered}, पसंदीदा संदर्भ {reference} से बाहर है। इसे अपने आप फसल की असफलता नहीं माना गया है।'
        elif code == 'LOCAL_WATER_ESTIMATE_REQUIRED': text=f'आपका पानी {entered}, संदर्भ {reference} के बीच आता है। असली स्थानीय जरूरत इस सीमा में कहाँ होगी, यह पक्का करना बाकी है।'
        elif code == 'WATER_REFERENCE_SHORTFALL': text=f'आपका पानी {entered}, संदर्भ {reference} की निचली मात्रा से कम है। इस तुलना में पानी की कमी दिखती है, लेकिन इससे ठीक कितनी अतिरिक्त सिंचाई चाहिए यह तय नहीं होता।'
        elif code in {'INCOMPATIBLE_WATER_BASIS','INCOMPATIBLE_WATER_UNITS'}: text='आपका पानी का माप और फसल का संदर्भ एक ही तरह की मात्रा नहीं बताते। सही इकाई और पूरे मौसम या केवल अतिरिक्त सिंचाई का आधार पक्का करें।'
        elif code == 'DRAINAGE_MISMATCH': text='संदर्भ में अच्छी जल निकासी चाहिए, लेकिन आपके खेत में पानी रुकने की जानकारी दी गई है। इस स्थिति की स्थानीय जाँच जरूरी है।'
        elif code == 'NON_EXHAUSTIVE_EVIDENCE': text=f'संदर्भ {reference} कुछ बताई गई स्थितियाँ दिखाता है। आपकी जानकारी {entered} अलग है; केवल सूची में न होने से अनुपयुक्तता पक्की नहीं होती।'
        elif check['status']=='satisfied': text=f'आपकी जानकारी {entered}, फसल के संदर्भ {reference} से मेल खाती है। यह इस जाँच का मेल है, अच्छी पैदावार की गारंटी नहीं।'
        elif check['status']=='violated': text=f'आपकी जानकारी {entered}, दर्ज संदर्भ {reference} से मेल नहीं खाती। फसल चुनने से पहले इस अंतर की जाँच करें।'
        else:text=f'आपकी जानकारी {entered} और उपलब्ध संदर्भ {reference} से इस जाँच का पक्का नतीजा नहीं निकलता। और जानकारी या स्थानीय समीक्षा चाहिए।'
    else:
        if code == 'MISSING_USER_INPUT':text='ਇਸ ਜਾਂਚ ਲਈ ਲੋੜੀਂਦਾ ਮਾਪ ਜਾਂ ਖੇਤ ਦੀ ਜਾਣਕਾਰੀ ਨਹੀਂ ਦਿੱਤੀ ਗਈ। ਇਸ ਨੂੰ ਮੇਲ ਖਾਂਦਾ ਨਤੀਜਾ ਨਹੀਂ ਮੰਨਿਆ ਗਿਆ।'
        elif code == 'MISSING_VERIFIED_FACT':text='ਇਸ ਫ਼ਸਲ ਅਤੇ ਥਾਂ ਲਈ ਲਾਗੂ ਪ੍ਰਕਾਸ਼ਿਤ ਹਵਾਲਾ ਅਜੇ ਉਪਲਬਧ ਨਹੀਂ। ਇਸ ਦਾ ਮਤਲਬ ਫ਼ਸਲ ਅਣਢੁੱਕਵੀਂ ਹੋਣਾ ਨਹੀਂ; ਸਥਾਨਕ ਜਾਣਕਾਰੀ ਚਾਹੀਦੀ ਹੈ।'
        elif code == 'OUTSIDE_PREFERRED_RANGE':text=f'ਤੁਹਾਡਾ pH {entered}, ਪਸੰਦੀਦਾ ਹਵਾਲੇ {reference} ਤੋਂ ਬਾਹਰ ਹੈ। ਇਸ ਨੂੰ ਆਪਣੇ ਆਪ ਫ਼ਸਲ ਦੀ ਅਸਫਲਤਾ ਨਹੀਂ ਮੰਨਿਆ ਗਿਆ।'
        elif code == 'LOCAL_WATER_ESTIMATE_REQUIRED':text=f'ਤੁਹਾਡਾ ਪਾਣੀ {entered}, ਹਵਾਲੇ {reference} ਦੇ ਵਿਚਕਾਰ ਆਉਂਦਾ ਹੈ। ਅਸਲ ਸਥਾਨਕ ਲੋੜ ਇਸ ਹੱਦ ਵਿੱਚ ਕਿੱਥੇ ਹੋਵੇਗੀ, ਇਹ ਪੱਕਾ ਕਰਨਾ ਬਾਕੀ ਹੈ।'
        elif code == 'WATER_REFERENCE_SHORTFALL':text=f'ਤੁਹਾਡਾ ਪਾਣੀ {entered}, ਹਵਾਲੇ {reference} ਦੀ ਹੇਠਲੀ ਮਾਤਰਾ ਤੋਂ ਘੱਟ ਹੈ। ਇਸ ਤੁਲਨਾ ਵਿੱਚ ਪਾਣੀ ਦੀ ਘਾਟ ਦਿਸਦੀ ਹੈ ਪਰ ਇਸ ਨਾਲ ਵਾਧੂ ਸਿੰਚਾਈ ਦੀ ਸਹੀ ਮਾਤਰਾ ਤੈਅ ਨਹੀਂ ਹੁੰਦੀ।'
        elif code in {'INCOMPATIBLE_WATER_BASIS','INCOMPATIBLE_WATER_UNITS'}:text='ਤੁਹਾਡਾ ਪਾਣੀ ਦਾ ਮਾਪ ਅਤੇ ਫ਼ਸਲ ਦਾ ਹਵਾਲਾ ਇੱਕੋ ਕਿਸਮ ਦੀ ਮਾਤਰਾ ਨਹੀਂ ਦੱਸਦੇ। ਸਹੀ ਇਕਾਈ ਅਤੇ ਪੂਰੇ ਮੌਸਮ ਜਾਂ ਸਿਰਫ਼ ਵਾਧੂ ਸਿੰਚਾਈ ਦਾ ਆਧਾਰ ਪੱਕਾ ਕਰੋ।'
        elif code == 'DRAINAGE_MISMATCH':text='ਹਵਾਲੇ ਵਿੱਚ ਚੰਗੀ ਨਿਕਾਸੀ ਚਾਹੀਦੀ ਹੈ ਪਰ ਤੁਹਾਡੇ ਖੇਤ ਵਿੱਚ ਪਾਣੀ ਖੜ੍ਹਨ ਦੀ ਜਾਣਕਾਰੀ ਹੈ। ਇਸ ਹਾਲਤ ਦੀ ਸਥਾਨਕ ਜਾਂਚ ਜ਼ਰੂਰੀ ਹੈ।'
        elif code == 'NON_EXHAUSTIVE_EVIDENCE':text=f'ਹਵਾਲਾ {reference} ਕੁਝ ਦੱਸੀਆਂ ਹਾਲਤਾਂ ਦਿਖਾਉਂਦਾ ਹੈ। ਤੁਹਾਡੀ ਜਾਣਕਾਰੀ {entered} ਵੱਖਰੀ ਹੈ; ਸਿਰਫ਼ ਸੂਚੀ ਵਿੱਚ ਨਾ ਹੋਣ ਨਾਲ ਅਣਢੁੱਕਵਾਂ ਹੋਣਾ ਪੱਕਾ ਨਹੀਂ ਹੁੰਦਾ।'
        elif check['status']=='satisfied':text=f'ਤੁਹਾਡੀ ਜਾਣਕਾਰੀ {entered}, ਫ਼ਸਲ ਦੇ ਹਵਾਲੇ {reference} ਨਾਲ ਮੇਲ ਖਾਂਦੀ ਹੈ। ਇਹ ਇਸ ਜਾਂਚ ਦਾ ਮੇਲ ਹੈ, ਚੰਗੇ ਝਾੜ ਦੀ ਗਾਰੰਟੀ ਨਹੀਂ।'
        elif check['status']=='violated':text=f'ਤੁਹਾਡੀ ਜਾਣਕਾਰੀ {entered}, ਦਰਜ ਹਵਾਲੇ {reference} ਨਾਲ ਮੇਲ ਨਹੀਂ ਖਾਂਦੀ। ਫ਼ਸਲ ਚੁਣਨ ਤੋਂ ਪਹਿਲਾਂ ਇਸ ਫ਼ਰਕ ਦੀ ਜਾਂਚ ਕਰੋ।'
        else:text=f'ਤੁਹਾਡੀ ਜਾਣਕਾਰੀ {entered} ਅਤੇ ਹਵਾਲੇ {reference} ਤੋਂ ਇਸ ਜਾਂਚ ਦਾ ਪੱਕਾ ਨਤੀਜਾ ਨਹੀਂ ਨਿਕਲਦਾ। ਹੋਰ ਜਾਣਕਾਰੀ ਜਾਂ ਸਥਾਨਕ ਸਮੀਖਿਆ ਚਾਹੀਦੀ ਹੈ।'
    return text, IMPLICATIONS[language][index]


PLAN_TEXT = {
 'hi':[
  ('स्थानीय बुवाई का समय और किस्म पक्की करें','बोने का मौसम, अपने इलाके की मौजूदा बुवाई अवधि और उपयुक्त बीज की किस्म कृषि सलाहकार से पक्की करें। मौसम मेल खाने से हर किस्म की बुवाई की तारीख एक जैसी नहीं हो जाती।'),
  ('पानी की मात्रा और उपलब्धता पक्की करें','पूरे मौसम की उपयोगी बारिश, मिट्टी में मौजूद नमी और भरोसेमंद सिंचाई को अलग-अलग समझें। स्थानीय जरूरत और पानी मिलने का समय जाँचें। नीचे का संदर्भ एक बार की सिंचाई में देने की मात्रा नहीं है।'),
  ('मिट्टी और पानी निकलने की स्थिति जाँचें','मिट्टी-जाँच रिपोर्ट या स्थानीय जाँच से मिट्टी का प्रकार पक्का करें। जहाँ संदर्भ में अच्छी जल निकासी चाहिए, देखें कि बारिश के बाद पानी खेत से निकलता है या रुकता है। केवल मिट्टी का नाम मिलने से लवणता या हर खेत की स्थिति पक्की नहीं होती।'),
  ('मिट्टी-जाँच रिपोर्ट का pH देखें','अनुमान के बजाय मापा गया pH लें। पसंदीदा सीमा से बाहर नतीजे पर फसल को अपने आप खारिज न करें; स्थानीय सलाह लें। अकेले pH से खाद या उपचार की मात्रा तय नहीं होती।')],
 'pa':[
  ('ਸਥਾਨਕ ਬਿਜਾਈ ਦਾ ਸਮਾਂ ਅਤੇ ਕਿਸਮ ਪੱਕੀ ਕਰੋ','ਬੀਜਣ ਦਾ ਮੌਸਮ, ਆਪਣੇ ਇਲਾਕੇ ਦੀ ਮੌਜੂਦਾ ਬਿਜਾਈ ਮਿਆਦ ਅਤੇ ਢੁੱਕਵੀਂ ਬੀਜ ਕਿਸਮ ਖੇਤੀ ਸਲਾਹਕਾਰ ਤੋਂ ਪੱਕੀ ਕਰੋ। ਮੌਸਮ ਮੇਲ ਖਾਣ ਨਾਲ ਹਰ ਕਿਸਮ ਦੀ ਬਿਜਾਈ ਦੀ ਤਾਰੀਖ ਇੱਕੋ ਨਹੀਂ ਹੋ ਜਾਂਦੀ।'),
  ('ਪਾਣੀ ਦੀ ਮਾਤਰਾ ਅਤੇ ਉਪਲਬਧਤਾ ਪੱਕੀ ਕਰੋ','ਪੂਰੇ ਮੌਸਮ ਦੇ ਲਾਭਕਾਰੀ ਮੀਂਹ, ਮਿੱਟੀ ਦੀ ਨਮੀ ਅਤੇ ਭਰੋਸੇਯੋਗ ਸਿੰਚਾਈ ਨੂੰ ਵੱਖ-ਵੱਖ ਸਮਝੋ। ਸਥਾਨਕ ਲੋੜ ਅਤੇ ਪਾਣੀ ਮਿਲਣ ਦਾ ਸਮਾਂ ਜਾਂਚੋ। ਹੇਠਲਾ ਹਵਾਲਾ ਇੱਕ ਵਾਰ ਦੀ ਸਿੰਚਾਈ ਵਿੱਚ ਦੇਣ ਦੀ ਮਾਤਰਾ ਨਹੀਂ ਹੈ।'),
  ('ਮਿੱਟੀ ਅਤੇ ਪਾਣੀ ਨਿਕਲਣ ਦੀ ਹਾਲਤ ਜਾਂਚੋ','ਮਿੱਟੀ-ਜਾਂਚ ਰਿਪੋਰਟ ਜਾਂ ਸਥਾਨਕ ਜਾਂਚ ਤੋਂ ਮਿੱਟੀ ਦੀ ਕਿਸਮ ਪੱਕੀ ਕਰੋ। ਜਿੱਥੇ ਹਵਾਲੇ ਵਿੱਚ ਚੰਗੀ ਨਿਕਾਸੀ ਚਾਹੀਦੀ ਹੈ, ਵੇਖੋ ਕਿ ਮੀਂਹ ਤੋਂ ਬਾਅਦ ਪਾਣੀ ਨਿਕਲਦਾ ਹੈ ਜਾਂ ਖੜ੍ਹਦਾ ਹੈ। ਸਿਰਫ਼ ਮਿੱਟੀ ਦਾ ਨਾਮ ਮੇਲ ਖਾਣ ਨਾਲ ਖਾਰਾਪਣ ਜਾਂ ਹਰ ਹਾਲਤ ਪੱਕੀ ਨਹੀਂ ਹੁੰਦੀ।'),
  ('ਮਿੱਟੀ-ਜਾਂਚ ਰਿਪੋਰਟ ਦਾ pH ਵੇਖੋ','ਅੰਦਾਜ਼ੇ ਦੀ ਥਾਂ ਮਾਪਿਆ ਹੋਇਆ pH ਲਵੋ। ਪਸੰਦੀਦਾ ਹੱਦ ਤੋਂ ਬਾਹਰ ਨਤੀਜੇ ਉੱਤੇ ਫ਼ਸਲ ਨੂੰ ਆਪਣੇ ਆਪ ਰੱਦ ਨਾ ਕਰੋ; ਸਥਾਨਕ ਸਲਾਹ ਲਵੋ। ਸਿਰਫ਼ pH ਤੋਂ ਖਾਦ ਜਾਂ ਇਲਾਜ ਦੀ ਮਾਤਰਾ ਤੈਅ ਨਹੀਂ ਹੁੰਦੀ।')],
}


def plan_wording(action, language):
    if language == 'en':return action['title'], action['instruction']
    index=action['check_index']; title,instruction=PLAN_TEXT[language][index]
    if index==1 and any(r['status']=='violated' for r in action['references']):
        title={'hi':'फसल चुनने से पहले पानी की कमी जाँचें','pa':'ਫ਼ਸਲ ਚੁਣਨ ਤੋਂ ਪਹਿਲਾਂ ਪਾਣੀ ਦੀ ਘਾਟ ਜਾਂਚੋ'}[language]
    return title,instruction


def guidance_note(fact, language):
    name=CROPS.get(language,{}).get(fact['crop_id'],fact['crop_id'].replace('_',' ').title())
    value=fact['value']
    if fact['property']=='sowing_window':
        months={'hi':{'April':'अप्रैल','May':'मई','October':'अक्टूबर','November':'नवंबर'},'pa':{'April':'ਅਪ੍ਰੈਲ','May':'ਮਈ','October':'ਅਕਤੂਬਰ','November':'ਨਵੰਬਰ'}}
        for original,local in months.get(language,{}).items():value=value.replace(original,local)
        text={'en':f'{name}: published sowing window {value}.','hi':f'{name}: प्रकाशित बुवाई अवधि {value}।','pa':f'{name}: ਪ੍ਰਕਾਸ਼ਿਤ ਬਿਜਾਈ ਮਿਆਦ {value}।'}[language]
    else:
        interval=f'{value[0]}–{value[1]}'
        text={'en':f'{name}: indicative growing period {interval} days. The actual variety and local conditions can differ.','hi':f'{name}: संदर्भ में फसल अवधि {interval} दिन है। असली किस्म और स्थानीय स्थितियों से अवधि बदल सकती है।','pa':f'{name}: ਹਵਾਲੇ ਵਿੱਚ ਫ਼ਸਲ ਦੀ ਮਿਆਦ {interval} ਦਿਨ ਹੈ। ਅਸਲ ਕਿਸਮ ਅਤੇ ਸਥਾਨਕ ਹਾਲਤਾਂ ਨਾਲ ਮਿਆਦ ਬਦਲ ਸਕਦੀ ਹੈ।'}[language]
    return text+' '+LABELS[language]['guide']

FIELD_LABELS = {
 'hi':{'State / region':'राज्य / इलाका','District / town':'जिला / कस्बा','Growing season':'बुवाई का मौसम','Soil texture':'मिट्टी का प्रकार','Soil pH':'मिट्टी का pH','Field drainage':'खेत की जल निकासी','Water budget':'उपयोगी पानी का अनुमान','Water measurement':'पानी के माप का आधार','Observed rain this season':'इस मौसम में देखी गई बारिश','Measured seasonal rainfall':'मापी गई मौसमी बारिश','Field water source':'खेत में पानी का स्रोत'},
 'pa':{'State / region':'ਰਾਜ / ਇਲਾਕਾ','District / town':'ਜ਼ਿਲ੍ਹਾ / ਕਸਬਾ','Growing season':'ਬਿਜਾਈ ਦਾ ਮੌਸਮ','Soil texture':'ਮਿੱਟੀ ਦੀ ਕਿਸਮ','Soil pH':'ਮਿੱਟੀ ਦਾ pH','Field drainage':'ਖੇਤ ਦੀ ਨਿਕਾਸੀ','Water budget':'ਵਰਤਣਯੋਗ ਪਾਣੀ ਦਾ ਅੰਦਾਜ਼ਾ','Water measurement':'ਪਾਣੀ ਦੇ ਮਾਪ ਦਾ ਆਧਾਰ','Observed rain this season':'ਇਸ ਮੌਸਮ ਵਿੱਚ ਵੇਖਿਆ ਮੀਂਹ','Measured seasonal rainfall':'ਮਾਪਿਆ ਮੌਸਮੀ ਮੀਂਹ','Field water source':'ਖੇਤ ਦੇ ਪਾਣੀ ਦਾ ਸਰੋਤ'},
}


def field_label(label, language):
    return FIELD_LABELS.get(language,{}).get(label,label)

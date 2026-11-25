"""Curated, deterministic cases for the public PRAGATI demo."""

SCENARIOS = {
    "Marriage assistance": {
        "transcript": "నా వయసు 22 సంవత్సరాలు. మా కుటుంబ ఆదాయం సంవత్సరానికి లక్ష రూపాయలు.",
        "translation": "I am 22 years old and my family earns about ₹1 lakh per year.",
        "profile": {
            "age": 22,
            "annual_income": 100000,
            "location": "Telangana",
            "additional_notes": "Exploring marriage assistance",
        },
        "scheme": "Kalyana Lakshmi / Shaadi Mubarak",
        "response": (
            "మీ వివరాల ప్రకారం కళ్యాణ లక్ష్మి / షాదీ ముబారక్ పథకం ఒక సంభావ్య ఎంపిక. "
            "అధికారిక పోర్టల్‌లో మీ సామాజిక వర్గం, నివాసం మరియు ఆదాయ పత్రాలను ధృవీకరించండి."
        ),
        "reason": "The sample age, Telangana residence, and reported income align with headline criteria, subject to category and document checks.",
        "source": "https://rajannasircilla.telangana.gov.in/scheme/kalyana-lakshmi-shaadi-mubarak/",
    },
    "Pregnancy support": {
        "transcript": "నేను గర్భవతిని. ప్రభుత్వ ఆసుపత్రిలో నమోదు చేసుకున్నాను.",
        "translation": "I am pregnant and registered at a government hospital.",
        "profile": {
            "location": "Telangana",
            "pregnant": True,
            "government_hospital_registered": True,
        },
        "scheme": "KCR Kit",
        "response": (
            "మీరు ప్రభుత్వ ఆసుపత్రిలో నమోదు చేసుకున్నందున KCR Kit గురించి అక్కడి ANM లేదా ASHA "
            "కార్యకర్తను అడగండి. తుది అర్హతను ఆసుపత్రి సిబ్బంది ధృవీకరిస్తారు."
        ),
        "reason": "The official programme is designed around pregnancy care and delivery through government facilities.",
        "source": "https://yadadri.telangana.gov.in/scheme/kcr-kit/",
    },
    "Hospital treatment": {
        "transcript": "మా కుటుంబం తక్కువ ఆదాయ వర్గానికి చెందినది. పెద్ద వైద్య చికిత్స అవసరం.",
        "translation": "My family is low income and needs major medical treatment.",
        "profile": {
            "location": "Telangana",
            "low_income_household": True,
            "needs_hospital_treatment": True,
        },
        "scheme": "Rajiv Aarogyasri / Cheyutha",
        "response": (
            "రాజీవ్ ఆరోగ్యశ్రీ / చేయూత పథకంలో మీ చికిత్స కవర్ అవుతుందో తెలుసుకోవడానికి సమీపంలోని "
            "నెట్‌వర్క్ ఆసుపత్రి లేదా ఆరోగ్యమిత్రను సంప్రదించండి."
        ),
        "reason": "The programme supports eligible low-income households through empanelled hospitals; coverage depends on current rules and the treatment package.",
        "source": "https://www.telangana.gov.in/government-initiatives/",
    },
    "Single-woman pension": {
        "transcript": "నేను గ్రామంలో నివసించే 32 సంవత్సరాల అవివాహిత మహిళను. నాకు స్థిరమైన ఆదాయం లేదు.",
        "translation": "I am a 32-year-old unmarried woman in a rural area without stable income.",
        "profile": {
            "age": 32,
            "marital_status": "unmarried",
            "area": "rural",
            "stable_income": False,
        },
        "scheme": "Single Women Pension",
        "response": (
            "మీ వివరాలు Single Women Pension పథకానికి సంభావ్యంగా సరిపోవచ్చు. "
            "MeeSeva ద్వారా ప్రస్తుత ఆదాయ, వయస్సు మరియు ఇతర అర్హత నియమాలను ధృవీకరించండి."
        ),
        "reason": "The illustrative profile matches the published rural age threshold, but income, other pensions, and documentation still require official verification.",
        "source": "https://jagtial.telangana.gov.in/scheme/single-women-pension-scheme/",
    },
}


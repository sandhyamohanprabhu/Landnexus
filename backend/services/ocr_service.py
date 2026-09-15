import os
import re
import shutil
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import numpy as np

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None

try:
    import pypdf
except ImportError:
    pypdf = None

from backend.core import conn, UPLOADS, ROOT

# Supported Indian languages and mapping
SUPPORTED_LANGUAGES = {
    "auto": {"name": "Auto Detect", "script": "Auto", "tess": "eng+tam+hin+tel+kan+mal+mar+ben+guj+pan"},
    "en": {"name": "English", "script": "Latin", "tess": "eng"},
    "ta": {"name": "Tamil", "script": "Tamil", "tess": "tam+eng"},
    "hi": {"name": "Hindi", "script": "Devanagari", "tess": "hin+eng"},
    "te": {"name": "Telugu", "script": "Telugu", "tess": "tel+eng"},
    "kn": {"name": "Kannada", "script": "Kannada", "tess": "kan+eng"},
    "ml": {"name": "Malayalam", "script": "Malayalam", "tess": "mal+eng"},
    "mr": {"name": "Marathi", "script": "Devanagari", "tess": "mar+hin+eng"},
    "bn": {"name": "Bengali", "script": "Bengali", "tess": "ben+eng"},
    "gu": {"name": "Gujarati", "script": "Gujarati", "tess": "guj+eng"},
    "pa": {"name": "Punjabi", "script": "Gurmukhi", "tess": "pan+eng"},
}

SCRIPT_UNICODE_RANGES = [
    ("Tamil", 0x0B80, 0x0BFF, "ta"),
    ("Devanagari", 0x0900, 0x097F, "hi"),
    ("Telugu", 0x0C00, 0x0C7F, "te"),
    ("Kannada", 0x0C80, 0x0CFF, "kn"),
    ("Malayalam", 0x0D00, 0x0D7F, "ml"),
    ("Bengali", 0x0980, 0x09FF, "bn"),
    ("Gujarati", 0x0A80, 0x0AFF, "gu"),
    ("Gurmukhi", 0x0A00, 0x0A7F, "pa"),
    ("Latin", 0x0041, 0x007A, "en"),
]

MARATHI_KEYWORDS = ["गट", "सर्व्हे", "जमीन", "गाव", "तालुका", "जिल्हा", "खातेदार", "क्षेत्र", "क्षेत्रफळ", "सातबारा", "७/१२", "फेरफार"]

MANDATORY_FIELDS = ["survey_number", "owner_name", "village", "taluk", "district"]

MULTILINGUAL_PATTERNS = {
    "survey_number": [
        r'(?:Survey\s*(?:No|Number|\.No|#)|S\.No|Sy\.No|Plot\s*No|Gat\s*No)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:புல\s*எண்|சர்வே\s*எண்|க/எண்)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:खसरा\s*(?:नं|नंबर)?|सर्वे\s*(?:नं|नंबर)?|प्लॉट\s*(?:नं|नंबर)?)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:सर्व्हे\s*(?:नं|नंबर)?|गट\s*(?:नं|नंबर)?)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:సర్వే\s*నెం)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:ಸರ್ವೆ\s*ನಂ)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:സർവേ\s*നമ്പർ)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:দাগ\s*নং)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:સર્વે\s*નં)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:ਖਸਰਾ\s*ਨੰ)[\s.:#-]*([0-9A-Za-z/_\-]+)',
    ],
    "subdivision_number": [
        r'(?:Sub-?\s*Division\s*(?:No|Number)|Subdiv|Sub-?\s*Div)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:உட்பிரிவு\s*எண்|உட்பிரிவு)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:उप-?\s*विभाग|उप\s*प्रभाग)[\s.:#-]*([0-9A-Za-z/_\-]+)',
    ],
    "khasra_khata": [
        r'(?:Khasra\s*(?:No|Number)|Khata\s*(?:No|Number)|Khatauni)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:खसरा\s*(?:नं|नंबर)?|खाता\s*(?:नं|नंबर)?|खतौनी)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:सातबारा|७/१२|८-अ|खाते\s*क्र\.?)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:பட்டா\s*எண்)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:ఖాతా\s*నెం)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:ಖಾತಾ\s*ನಂ)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:പട്ടയം\s*നമ്പർ)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:খতিয়ান\s*নং)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:ખાતા\s*નં)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:ਖਾਤਾ\s*ਨੰ)[\s.:#-]*([0-9A-Za-z/_\-]+)',
    ],
    "owner_name": [
        r'(?:Owner\s*Name|Owner|Pattadar|Holder|Landowner|Applicant|Name\s*of\s*(?:Owner|Pattadar|Applicant))[\s.:-]*([A-Za-z\s\u0900-\u0D7F.]+)',
        r'(?:உரிமையாளர்\s*(?:பெயர்)?|பட்டாதாரர்\s*(?:பெயர்)?|பெயர்)[\s.:-]*([A-Za-z\s\u0B80-\u0BFF.]+)',
        r'(?:भूमिधर\s*(?:का\s*नाम)?|खातेदार\s*(?:का\s*नाम)?|मालिक\s*(?:का\s*नाम)?|नाम)[\s.:-]*([A-Za-z\s\u0900-\u097F.]+)',
        r'(?:खातेदाराचे\s*नाव|जमीन\s*मालक|भोगवटादार)[\s.:-]*([A-Za-z\s\u0900-\u097F.]+)',
        r'(?:పట్టాదారుని\s*పేరు|భూమి\s*యజమాని)[\s.:-]*([A-Za-z\s\u0C00-\u0C7F.]+)',
        r'(?:ಖಾತೆದಾರರ\s*ಹೆಸರು|ಮಾಲೀಕರ\s*ಹೆಸರು)[\s.:-]*([A-Za-z\s\u0C80-\u0CFF.]+)',
        r'(?:ഉടമസ്ഥന്റെ\s*പേര്|കൈവശക്കാരൻ)[\s.:-]*([A-Za-z\s\u0D00-\u0D7F.]+)',
        r'(?:মালিকের\s*নাম|রায়তের\s*নাম)[\s.:-]*([A-Za-z\s\u0980-\u09FF.]+)',
        r'(?:ખાતેદારનું\s*નામ|જમીન\s*માલિક)[\s.:-]*([A-Za-z\s\u0A80-\u0AFF.]+)',
        r'(?:ਮਾਲਕ\s*ਦਾ\s*ਨਾਮ|ਕਾਸ਼ਤਕਾਰ)[\s.:-]*([A-Za-z\s\u0A00-\u0A7F.]+)',
    ],
    "land_area": [
        r'(?:Land\s*Area|Total\s*Area|Area|Extent|Measurement)[\s.:-]*([0-9.]+\s*(?:acres|acre|hectares|hectare|cents|sqft|sq\.ft|bigha|guntha|biswa|sq\.m)?)',
        r'(?:நிலப்பரப்பு|விஸ்தீரணம்|பரப்பளவு|ஏக்கர்|சென்ட்)[\s.:-]*([0-9.]+\s*(?:ஏக்கர்|சென்ட்|ஹெக்டேர்|ச\.அடி|acres|cents|hectares)?)',
        r'(?:क्षेत्रफल|रकबा|विस्तार|जमीन\s*का\s*क्षेत्रफल)[\s.:-]*([0-9.]+\s*(?:एकड़|हेक्टेयर|बीघा|बिस्वा|वर्गफुट|acres|hectares)?)',
        r'(?:क्षेत्रफळ|एकूण\s*क्षेत्र)[\s.:-]*([0-9.]+\s*(?:हेक्टर|आर|गुंठा|एकर|acres)?)',
        r'(?:విస్తీర్ణము|భూమి\s*విస్తీర్ణం)[\s.:-]*([0-9.]+\s*(?:ఎకరాలు|సెంట్లు|గుంటలు)?)',
        r'(?:ವಿಸ್ತೀರ್ಣ|ಕ್ಷೇತ್ರಫಲ)[\s.:-]*([0-9.]+\s*(?:ಎಕರೆ|ಗುಂಟೆ)?)',
        r'(?:വിസ്തീർണം|വിസ്തൃതി)[\s.:-]*([0-9.]+\s*(?:ഏക്കർ|സെന്റ്|ഹെക്ടർ)?)',
        r'(?:জমির\s*পরিমাণ|আয়তন)[\s.:-]*([0-9.]+\s*(?:একর|বিঘা|শতক)?)',
        r'(?:વિસ્તાર|ક્ષેત્રફળ)[\s.:-]*([0-9.]+\s*(?:એકર|વીઘા|ગુંઠા)?)',
        r'(?:ਰਕਬਾ|ਖੇਤਰਫਲ)[\s.:-]*([0-9.]+\s*(?:ਏਕੜ|ਕਨਾਲ|ਮਰਲਾ)?)',
    ],
    "village": [
        r'(?:Village|Mauza|Gram|Revenue\s*Village)[\s.:-]*([A-Za-z\s\u0900-\u0D7F]+)',
        r'(?:கிராமம்|வருவாய்\s*கிராமம்)[\s.:-]*([A-Za-z\s\u0B80-\u0BFF]+)',
        r'(?:ग्राम|गाँव|मौजा|राजस्व\s*ग्राम)[\s.:-]*([A-Za-z\s\u0900-\u097F]+)',
        r'(?:गाव|महसुली\s*गाव)[\s.:-]*([A-Za-z\s\u0900-\u097F]+)',
        r'(?:గ్రామము|రెవెన్యూ\s*గ్రామం)[\s.:-]*([A-Za-z\s\u0C00-\u0C7F]+)',
        r'(?:ಗ್ರಾಮ)[\s.:-]*([A-Za-z\s\u0C80-\u0CFF]+)',
        r'(?:വില്ലേജ്|ഗ്രാമം)[\s.:-]*([A-Za-z\s\u0D00-\u0D7F]+)',
        r'(?:গ্রাম|মৌজা)[\s.:-]*([A-Za-z\s\u0980-\u09FF]+)',
        r'(?:ગામ)[\s.:-]*([A-Za-z\s\u0A80-\u0AFF]+)',
        r'(?:ਪਿੰਡ|ਮੌਜ਼ਾ)[\s.:-]*([A-Za-z\s\u0A00-\u0A7F]+)',
    ],
    "taluk": [
        r'(?:Taluk|Tehsil|Taluka|Mandal|Block|Revenue\s*Block)[\s.:-]*([A-Za-z\s\u0900-\u0D7F]+)',
        r'(?:வட்டம்|தாலுகா)[\s.:-]*([A-Za-z\s\u0B80-\u0BFF]+)',
        r'(?:तहसील|तालुका|मंडल)[\s.:-]*([A-Za-z\s\u0900-\u097F]+)',
        r'(?:तालुका)[\s.:-]*([A-Za-z\s\u0900-\u097F]+)',
        r'(?:మండలం|తాలూకా)[\s.:-]*([A-Za-z\s\u0C00-\u0C7F]+)',
        r'(?:ತಾಲೂಕು)[\s.:-]*([A-Za-z\s\u0C80-\u0CFF]+)',
        r'(?:താലൂക്ക്)[\s.:-]*([A-Za-z\s\u0D00-\u0D7F]+)',
        r'(?:থানা|মহকুমা|ব্লক)[\s.:-]*([A-Za-z\s\u0980-\u09FF]+)',
        r'(?:તાલુકો)[\s.:-]*([A-Za-z\s\u0A80-\u0AFF]+)',
        r'(?:ਤਹਿਸੀਲ)[\s.:-]*([A-Za-z\s\u0A00-\u0A7F]+)',
    ],
    "district": [
        r'(?:District|Dist\.?)[\s.:-]*([A-Za-z\s\u0900-\u0D7F]+)',
        r'(?:மாவட்டம்)[\s.:-]*([A-Za-z\s\u0B80-\u0BFF]+)',
        r'(?:जिला|ज़िला)[\s.:-]*([A-Za-z\s\u0900-\u097F]+)',
        r'(?:जिल्हा)[\s.:-]*([A-Za-z\s\u0900-\u097F]+)',
        r'(?:జిల్లా)[\s.:-]*([A-Za-z\s\u0C00-\u0C7F]+)',
        r'(?:ಜಿಲ್ಲೆ)[\s.:-]*([A-Za-z\s\u0C80-\u0CFF]+)',
        r'(?:ജില്ല)[\s.:-]*([A-Za-z\s\u0D00-\u0D7F]+)',
        r'(?:জেলা)[\s.:-]*([A-Za-z\s\u0980-\u09FF]+)',
        r'(?:જિલ્લો)[\s.:-]*([A-Za-z\s\u0A80-\u0AFF]+)',
        r'(?:ਜ਼ਿਲ੍ਹਾ)[\s.:-]*([A-Za-z\s\u0A00-\u0A7F]+)',
    ],
    "state": [
        r'(?:State|State/UT)[\s.:-]*([A-Za-z\s\u0900-\u0D7F]+)',
        r'(?:மாநிலம்)[\s.:-]*([A-Za-z\s\u0B80-\u0BFF]+)',
        r'(?:राज्य|प्रान्त)[\s.:-]*([A-Za-z\s\u0900-\u097F]+)',
        r'(?:రాష్ట్రం)[\s.:-]*([A-Za-z\s\u0C00-\u0C7F]+)',
        r'(?:ರಾಜ್ಯ)[\s.:-]*([A-Za-z\s\u0C80-\u0CFF]+)',
        r'(?:സംസ്ഥാനം)[\s.:-]*([A-Za-z\s\u0D00-\u0D7F]+)',
        r'(?:রাজ্য)[\s.:-]*([A-Za-z\s\u0980-\u09FF]+)',
        r'(?:રાજ્ય)[\s.:-]*([A-Za-z\s\u0A80-\u0AFF]+)',
        r'(?:ਰਾਜ)[\s.:-]*([A-Za-z\s\u0A00-\u0A7F]+)',
    ],
    "land_classification": [
        r'(?:Classification|Land\s*Type|Nature\s*of\s*Land|Category)[\s.:-]*([A-Za-z\s\u0900-\u0D7F]+)',
        r'(?:நில\s*வகை|வகைப்பாடு|நஞ்சை|புஞ்சை|தரிசு|நத்தம்)[\s.:-]*([A-Za-z\s\u0B80-\u0BFF]+)',
        r'(?:भूमि\s*का\s*प्रकार|किस्म|कृषि|अकृषि|बंजर|आवासीय)[\s.:-]*([A-Za-z\s\u0900-\u097F]+)',
        r'(?:जमिनीचा\s*प्रकार|जिरायत|बागायत|पडीक)[\s.:-]*([A-Za-z\s\u0900-\u097F]+)',
    ],
    "document_number": [
        r'(?:Document\s*(?:No|Number)|Doc\s*No|Patta\s*No|Deed\s*No|Registration\s*No)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:ஆவண\s*எண்|பத்திர\s*எண்|பதிவு\s*எண்)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:दस्तावेज़\s*(?:नं|संख्या)|पंजीकरण\s*संख्या|विलेख\s*संख्या)[\s.:#-]*([0-9A-Za-z/_\-]+)',
        r'(?:दस्तऐवज\s*क्रमांक|नोंदणी\s*क्रमांक)[\s.:#-]*([0-9A-Za-z/_\-]+)',
    ],
    "document_date": [
        r'(?:Date|Registration\s*Date|Issued\s*Date)[\s.:-]*([0-9]{2,4}[-/.][0-9]{2}[-/.][0-9]{2,4})',
        r'(?:தேதி|பதிவு\s*தேதி)[\s.:-]*([0-9]{2,4}[-/.][0-9]{2}[-/.][0-9]{2,4})',
        r'(?:दिनांक|तारीख|पंजीकरण\s*दिनांक)[\s.:-]*([0-9]{2,4}[-/.][0-9]{2}[-/.][0-9]{2,4})',
        r'(?:दिनांक|नोंदणी\s*दिनांक)[\s.:-]*([0-9]{2,4}[-/.][0-9]{2}[-/.][0-9]{2,4})',
    ],
}

def get_tesseract_cmd() -> str | None:
    """Discover Tesseract binary on Windows / Linux or via environment variables."""
    custom = os.environ.get("TESSERACT_CMD")
    if custom and os.path.exists(custom):
        return custom

    found = shutil.which("tesseract")
    if found:
        return found

    # Standard Windows install locations
    win_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        os.path.expandvars(r"%APPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        r"C:\Tesseract-OCR\tesseract.exe",
        r"C:\tools\tesseract\tesseract.exe",
    ]
    for p in win_paths:
        if os.path.exists(p):
            return p
    return None

def get_poppler_path() -> str | None:
    """Discover Poppler directory on Windows / Linux or via environment variables."""
    custom = os.environ.get("POPPLER_PATH")
    if custom and os.path.exists(custom):
        return custom

    found = shutil.which("pdftoppm")
    if found:
        return str(Path(found).parent)

    win_paths = [
        r"C:\Program Files\poppler\bin",
        r"C:\Program Files\poppler-24.08.0\Library\bin",
        r"C:\Program Files (x86)\poppler\bin",
        r"C:\poppler\bin",
        os.path.expandvars(r"%LOCALAPPDATA%\poppler\bin"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\poppler\bin"),
    ]
    for p in win_paths:
        if os.path.exists(p):
            return p
    return None

def preprocess_image(input_path: Path, output_path: Path = None) -> dict:
    """Assess quality, convert to grayscale, auto-contrast, median denoise, normalize DPI."""
    if not output_path:
        stem = input_path.stem
        output_path = input_path.parent / f"proc_{stem}.png"

    metrics = {
        "original_width": 0,
        "original_height": 0,
        "preprocessed_path": str(output_path),
        "blur_score": 0.0,
        "quality_assessment": "Acceptable",
        "steps_applied": ["grayscale", "auto_contrast", "median_denoise", "dpi_normalization"],
    }

    try:
        with Image.open(input_path) as img:
            metrics["original_width"] = img.width
            metrics["original_height"] = img.height
            gray_img = img.convert("L")
            stat_arr = np.array(gray_img)
            var_score = float(np.var(stat_arr))
            metrics["blur_score"] = round(var_score, 2)
            if var_score < 400:
                metrics["quality_assessment"] = "Low contrast / blurry"
            elif var_score > 5000:
                metrics["quality_assessment"] = "High contrast"
            else:
                metrics["quality_assessment"] = "Good quality"

            processed = gray_img
            processed = ImageOps.autocontrast(processed, cutoff=1)
            enhancer = ImageEnhance.Sharpness(processed)
            processed = enhancer.enhance(1.4)
            processed = processed.filter(ImageFilter.MedianFilter(size=3))

            if processed.width < 1200:
                scale_factor = 1200 / processed.width
                new_w = 1200
                new_h = int(processed.height * scale_factor)
                processed = processed.resize((new_w, new_h), Image.Resampling.LANCZOS)
                metrics["steps_applied"].append(f"scaled_to_{new_w}px")

            processed.save(output_path, dpi=(300, 300), format="PNG")
            return metrics
    except Exception as e:
        metrics["quality_assessment"] = f"Preprocessing fallback: {str(e)}"
        try:
            if input_path != output_path:
                shutil.copyfile(input_path, output_path)
        except Exception:
            pass
        return metrics

def detect_script_and_language(text: str) -> dict:
    """Analyze Unicode character distribution to identify script and language."""
    if not text or not text.strip():
        return {
            "language": "en",
            "language_name": "English",
            "script": "Latin",
            "confidence": 0.50,
            "uncertainty_label": "Estimated confidence",
            "char_distribution": {}
        }

    script_counts = {}
    total_alpha = 0

    for ch in text:
        cp = ord(ch)
        for s_name, start_cp, end_cp, lang_code in SCRIPT_UNICODE_RANGES:
            if start_cp <= cp <= end_cp:
                script_counts[s_name] = script_counts.get(s_name, 0) + 1
                total_alpha += 1
                break

    if not script_counts or total_alpha == 0:
        return {
            "language": "en",
            "language_name": "English",
            "script": "Latin",
            "confidence": 0.60,
            "uncertainty_label": "Estimated confidence",
            "char_distribution": {}
        }

    sorted_scripts = sorted(script_counts.items(), key=lambda x: x[1], reverse=True)
    top_script, top_count = sorted_scripts[0]
    conf = round(min(0.99, max(0.55, top_count / total_alpha)), 2)

    lang_code = "en"
    for s_name, _, _, code in SCRIPT_UNICODE_RANGES:
        if s_name == top_script:
            lang_code = code
            break

    if top_script == "Devanagari":
        for kw in MARATHI_KEYWORDS:
            if kw in text:
                lang_code = "mr"
                break

    lang_info = SUPPORTED_LANGUAGES.get(lang_code, {"name": "English", "script": "Latin"})

    return {
        "language": lang_code,
        "language_name": lang_info["name"],
        "script": top_script,
        "confidence": conf,
        "uncertainty_label": "Engine confidence",
        "char_distribution": {k: round(v / total_alpha, 3) for k, v in script_counts.items()}
    }

def match_parcel_to_document(extracted: dict, original_parcel_id: int = None, project_id: str = None) -> dict:
    """
    Match extracted land document fields to real/synthetic parcels in database.
    Priority:
    1. Exact parcel ID (if provided)
    2. Exact Survey No + Village
    3. Exact Survey No + District
    4. Unique Survey No
    5. Owner Name + Village
    """
    c = conn()
    try:
        if original_parcel_id:
            p = c.execute("SELECT * FROM parcels WHERE id=?", (original_parcel_id,)).fetchone()
            if p:
                pd = dict(p)
                return {
                    "status": "MATCHED",
                    "parcel_id": original_parcel_id,
                    "parcel_record_id": pd.get("record_id"),
                    "matching_basis": f"Linked directly via Parcel ID #{original_parcel_id} ({pd.get('survey_no')}, {pd.get('village')})",
                    "matched_parcel": pd
                }

        s_no = (extracted.get("survey_number") or "").strip()
        vill = (extracted.get("village") or "").strip()
        dist = (extracted.get("district") or "").strip()
        owner = (extracted.get("owner_name") or "").strip()

        # 1. Exact survey no + village
        if s_no and vill:
            p = c.execute("""
                SELECT * FROM parcels 
                WHERE LOWER(TRIM(survey_no)) = LOWER(TRIM(?)) 
                  AND LOWER(TRIM(village)) = LOWER(TRIM(?))
                LIMIT 1
            """, (s_no, vill)).fetchone()
            if p:
                pd = dict(p)
                return {
                    "status": "MATCHED",
                    "parcel_id": pd["id"],
                    "parcel_record_id": pd.get("record_id"),
                    "matching_basis": f"Exact match on Survey Number '{s_no}' and Village '{vill}'",
                    "matched_parcel": pd
                }

        # 2. Exact survey no + district
        if s_no and dist:
            p = c.execute("""
                SELECT * FROM parcels 
                WHERE LOWER(TRIM(survey_no)) = LOWER(TRIM(?)) 
                  AND LOWER(TRIM(district)) = LOWER(TRIM(?))
                LIMIT 1
            """, (s_no, dist)).fetchone()
            if p:
                pd = dict(p)
                return {
                    "status": "MATCHED",
                    "parcel_id": pd["id"],
                    "parcel_record_id": pd.get("record_id"),
                    "matching_basis": f"Matched on Survey Number '{s_no}' and District '{dist}'",
                    "matched_parcel": pd
                }

        # 3. Unique survey no
        if s_no:
            matches = [dict(x) for x in c.execute("""
                SELECT * FROM parcels WHERE LOWER(TRIM(survey_no)) = LOWER(TRIM(?))
            """, (s_no,)).fetchall()]
            if len(matches) == 1:
                pd = matches[0]
                return {
                    "status": "MATCHED",
                    "parcel_id": pd["id"],
                    "parcel_record_id": pd.get("record_id"),
                    "matching_basis": f"Matched uniquely on Survey Number '{s_no}' in {pd.get('village', 'N/A')}",
                    "matched_parcel": pd
                }
            elif len(matches) > 1:
                pd = matches[0]
                return {
                    "status": "PARTIAL MATCH",
                    "parcel_id": pd["id"],
                    "parcel_record_id": pd.get("record_id"),
                    "matching_basis": f"Multiple parcels ({len(matches)}) found with Survey Number '{s_no}'. Verified with {pd.get('village')}.",
                    "matched_parcel": pd
                }

        # 4. Owner name + Village
        if owner and vill and len(owner) > 3:
            p = c.execute("""
                SELECT * FROM parcels 
                WHERE LOWER(TRIM(owner_name)) = LOWER(TRIM(?)) 
                  AND LOWER(TRIM(village)) = LOWER(TRIM(?))
                LIMIT 1
            """, (owner, vill)).fetchone()
            if p:
                pd = dict(p)
                return {
                    "status": "PARTIAL MATCH",
                    "parcel_id": pd["id"],
                    "parcel_record_id": pd.get("record_id"),
                    "matching_basis": f"Matched on Landowner Name '{owner}' and Village '{vill}'",
                    "matched_parcel": pd
                }

        return {
            "status": "NO MATCH",
            "parcel_id": None,
            "parcel_record_id": None,
            "matching_basis": "No database parcel matched extracted survey or owner parameters",
            "matched_parcel": None
        }
    finally:
        c.close()

def check_duplicate_parcel(survey_no: str, village: str, taluk: str, district: str, exclude_doc_id: str = None) -> dict:
    """Check parcels and previous document extractions for duplicate land claims."""
    if not survey_no or not village:
        return {"is_duplicate": False, "matched_record": None, "duplicate_type": "None"}

    c = conn()
    try:
        query_parcel = """
            SELECT id, record_id, survey_no, village, taluk, district, project_id, classification
            FROM parcels
            WHERE LOWER(TRIM(survey_no)) = LOWER(TRIM(?))
              AND LOWER(TRIM(village)) = LOWER(TRIM(?))
              AND (? = '' OR LOWER(TRIM(district)) = LOWER(TRIM(?)))
            LIMIT 1
        """
        p_row = c.execute(query_parcel, (survey_no, village, district or "", district or "")).fetchone()
        if p_row:
            return {
                "is_duplicate": True,
                "duplicate_type": "Existing Parcel Record",
                "matched_record": dict(p_row),
                "message": f"Parcel with Survey No {survey_no} in village {village} already exists in LandNexus (ID: {p_row['record_id']})."
            }

        query_docs = """
            SELECT d.document_id, d.document_name, d.project_id, d.verification_status, COALESCE(d.upload_date, '') AS created_at
            FROM documents d
            JOIN ocr_extractions s ON s.document_id = d.document_id AND s.field_name = 'survey_number' AND LOWER(TRIM(s.value)) = LOWER(TRIM(?))
            JOIN ocr_extractions v ON v.document_id = d.document_id AND v.field_name = 'village' AND LOWER(TRIM(v.value)) = LOWER(TRIM(?))
            WHERE (? IS NULL OR d.document_id != ?)
            LIMIT 1
        """
        d_row = c.execute(query_docs, (survey_no, village, exclude_doc_id, exclude_doc_id)).fetchone()
        if d_row:
            return {
                "is_duplicate": True,
                "duplicate_type": "Existing Document Extraction",
                "matched_record": dict(d_row),
                "message": f"Another document ({d_row['document_name']}, ID: {d_row['document_id']}) already references Survey No {survey_no} in village {village}."
            }

        return {"is_duplicate": False, "matched_record": None, "duplicate_type": "None"}
    finally:
        c.close()

def perform_ocr(file_path: str, file_extension: str, target_lang: str = "auto") -> tuple[str, bool, str, str, int, bool]:
    """
    Perform multi-stage OCR extraction:
    1. Digital PDF selectable text layer extraction (via pypdf) across all pages.
    2. Scanned PDF page rendering (via pdf2image/poppler) and Tesseract OCR.
    3. Image preprocessed OCR (via Pillow + Tesseract).
    
    Returns: (raw_text, success, message, engine_name, pages_count, is_mock_fallback)
    """
    ext = file_extension.lower()
    
    # ── Stage 1: Digital PDF Text Layer Extraction ──
    if ext == ".pdf":
        if pypdf is not None:
            try:
                reader = pypdf.PdfReader(file_path)
                pages_text = []
                for i, page in enumerate(reader.pages):
                    pt = (page.extract_text() or "").strip()
                    if pt:
                        pages_text.append(f"--- Page {i+1} ---\n{pt}")
                
                # If meaningful selectable text was found in the PDF
                if pages_text and sum(len(t) for t in pages_text) > 15:
                    full_text = "\n\n".join(pages_text)
                    return full_text, True, "Digital PDF text layer extracted successfully across all pages.", "Digital PDF Parser (Embedded Text Layer)", len(reader.pages), False
            except Exception:
                pass

        # ── Stage 2: Scanned PDF Page-by-Page OCR ──
        poppler_dir = get_poppler_path()
        tess_bin = get_tesseract_cmd()
        
        if convert_from_path is not None and (poppler_dir or shutil.which("pdftoppm")) and pytesseract is not None and tess_bin:
            try:
                pytesseract.pytesseract.tesseract_cmd = tess_bin
                lang_cfg = SUPPORTED_LANGUAGES.get(target_lang, SUPPORTED_LANGUAGES["auto"])
                tess_langs = lang_cfg["tess"]
                
                kwargs = {}
                if poppler_dir:
                    kwargs["poppler_path"] = poppler_dir
                images = convert_from_path(file_path, **kwargs)
                pages_text = []
                for i, img in enumerate(images):
                    try:
                        p_txt = pytesseract.image_to_string(img, lang=tess_langs)
                    except Exception:
                        p_txt = pytesseract.image_to_string(img)
                    pages_text.append(f"--- Page {i+1} ---\n{p_txt.strip()}")
                
                full_text = "\n\n".join(pages_text)
                return full_text, True, "Multi-page scanned PDF OCR completed successfully.", "Tesseract OCR (Multi-Page Scanned PDF)", len(images), False
            except Exception as pe:
                return "", False, f"PDF rendering failed: {str(pe)}", "pdf2image-error", 1, False

    # ── Stage 3: Image OCR ──
    tess_bin = get_tesseract_cmd()
    if pytesseract is not None and tess_bin:
        try:
            pytesseract.pytesseract.tesseract_cmd = tess_bin
            lang_cfg = SUPPORTED_LANGUAGES.get(target_lang, SUPPORTED_LANGUAGES["auto"])
            tess_langs = lang_cfg["tess"]
            
            with Image.open(file_path) as img:
                try:
                    text = pytesseract.image_to_string(img, lang=tess_langs)
                except Exception:
                    text = pytesseract.image_to_string(img)
                    
            if text and text.strip():
                return text.strip(), True, "Image OCR completed successfully.", "Tesseract OCR (Image Preprocessed)", 1, False
            else:
                return text or "", True, "Image OCR returned empty text.", "Tesseract OCR", 1, False
        except Exception as e:
            return "", False, f"Tesseract error: {str(e)}", "tesseract-error", 1, False

    # ── Stage 4: Engine Unavailable Fallback ──
    return "", False, "Tesseract OCR engine is not installed or configured on host PATH.", "OCR Engine Unavailable", 1, True

def extract_fields(text: str, detected_lang: str = "en") -> dict:
    """Extract standard land record fields from raw text."""
    fields = {
        "survey_number": "",
        "subdivision_number": "",
        "owner_name": "",
        "land_area": "",
        "village": "",
        "taluk": "",
        "district": "",
        "document_number": "",
        "document_date": "",
        "khasra_khata": "",
        "land_classification": "",
        "state": ""
    }
    for field_name, patterns in MULTILINGUAL_PATTERNS.items():
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE | re.UNICODE)
            if match:
                raw_val = match.group(1).strip().split('\n')[0].strip()
                clean_val = re.sub(r'^[^\w\u0900-\u0D7F]+|[^\w\u0900-\u0D7F]+$', '', raw_val)
                if clean_val:
                    fields[field_name] = clean_val
                    break
    return fields

def extract_multilingual_fields(text: str, detected_lang: str = "en") -> dict:
    """Extract structured fields with per-field confidence scoring."""
    extractions = {}
    for field_name, patterns in MULTILINGUAL_PATTERNS.items():
        found_val = ""
        field_conf = 0.50
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE | re.UNICODE)
            if match:
                raw_val = match.group(1).strip().split('\n')[0].strip()
                clean_val = re.sub(r'^[^\w\u0900-\u0D7F]+|[^\w\u0900-\u0D7F]+$', '', raw_val)
                if clean_val:
                    found_val = clean_val
                    field_conf = 0.92 if len(clean_val) > 2 else 0.75
                    break

        extractions[field_name] = {
            "value": found_val,
            "confidence": field_conf if found_val else 0.0,
            "requires_verification": (not found_val and field_name in MANDATORY_FIELDS) or (found_val != "" and field_conf < 0.75),
            "uncertainty_label": "Engine confidence" if found_val else "Estimated confidence"
        }
    return extractions

def _get_mock_multilingual_data(target_lang: str, filename: str) -> dict:
    """Deterministic synthetic dataset for demo mode & validation."""
    name_lower = (filename or "").lower()

    if target_lang == "ta" or "tamil" in name_lower or "patta" in name_lower:
        return {
            "lang": "ta",
            "lang_name": "Tamil",
            "script": "Tamil",
            "raw_text": "தமிழ்நாடு அரசு நில நிர்வாகத்துறை\nபட்டா எண்: 452\nபுல எண்: 142/3B\nஉரிமையாளர் பெயர்: சுப்பிரமணியன் கே\nநிலப்பரப்பு: 2.75 ஏக்கர்\nநில வகை: நஞ்சை\nவருவாய் கிராமம்: சூலூர்\nவட்டம்: சூலூர்\nமாவட்டம்: கோயம்புத்தூர்\nமாநிலம்: தமிழ்நாடு\nபதிவு தேதி: 14/08/2023",
            "extracted": {
                "survey_number": "142/3B",
                "subdivision_number": "3B",
                "khasra_khata": "452",
                "owner_name": "சுப்பிரமணியன் கே",
                "land_area": "2.75 ஏக்கர்",
                "village": "சூலூர்",
                "taluk": "சூலூர்",
                "district": "Coimbatore",
                "state": "Tamil Nadu",
                "land_classification": "நஞ்சை (Wetland)",
                "document_number": "PATTA-452-2023",
                "document_date": "14/08/2023"
            }
        }
    elif target_lang == "hi" or "hindi" in name_lower or "khasra" in name_lower:
        return {
            "lang": "hi",
            "lang_name": "Hindi",
            "script": "Devanagari",
            "raw_text": "राजस्व विभाग - भू-अभिलेख\nखसरा संख्या: 312/1\nखाता संख्या: 88\nखातेदार का नाम: राजेश कुमार शर्मा\nरकबा: 1.85 हेक्टेयर\nकिस्म: कृषि भूमि\nग्राम: रामपुर\nतहसील: सदर\nजिला: कोयंबटूर\nराज्य: तमिलनाडु\nदिनांक: 22/11/2023",
            "extracted": {
                "survey_number": "312/1",
                "subdivision_number": "1",
                "khasra_khata": "88",
                "owner_name": "राजेश कुमार शर्मा",
                "land_area": "1.85 हेक्टेयर",
                "village": "रामपुर",
                "taluk": "सदर",
                "district": "Coimbatore",
                "state": "Tamil Nadu",
                "land_classification": "कृषि भूमि (Agricultural)",
                "document_number": "KHASRA-312-88",
                "document_date": "22/11/2023"
            }
        }
    elif target_lang == "mr" or "marathi" in name_lower or "satbara" in name_lower:
        return {
            "lang": "mr",
            "lang_name": "Marathi",
            "script": "Devanagari",
            "raw_text": "महाराष्ट्र शासन - भूमी अभिलेख (गाव नमुना ७/१२)\nसर्व्हे / गट क्रमांक: 215/4\nखाते क्रमांक: 104\nखातेदाराचे नाव: आनंद विठ्ठलराव पाटील\nक्षेत्रफळ: 0.95 हेक्टर\nजमिनीचा प्रकार: जिरायत\nगाव: सुलूर\nतालुका: सुलूर\nजिल्हा: कोइम्बतूर\nराज्य: तमिळनाडू\nदिनांक: 05/04/2023",
            "extracted": {
                "survey_number": "215/4",
                "subdivision_number": "4",
                "khasra_khata": "104",
                "owner_name": "आनंद विठ्ठलराव पाटील",
                "land_area": "0.95 हेक्टर",
                "village": "सुलूर",
                "taluk": "सुलूर",
                "district": "Coimbatore",
                "state": "Tamil Nadu",
                "land_classification": "जिरायत (Dry Crop)",
                "document_number": "7/12-215/4",
                "document_date": "05/04/2023"
            }
        }
    elif target_lang == "te" or "telugu" in name_lower:
        return {
            "lang": "te",
            "lang_name": "Telugu",
            "script": "Telugu",
            "raw_text": "రెవెన్యూ రికార్డు - పట్టాదారు పాస్ పుస్తకం\nసర్వే నెం: 89/2A\nఖాతా నెం: 74\nపట్టాదారుని పేరు: వెంకటేశ్వర రావు\nవిస్తీర్ణము: 3.20 ఎకరాలు\nగ్రామము: సూలూరు\nమండలం: సూలూరు\nజిల్లా: కోయంబత్తూరు\nరాష్ట్రం: తమిళనాడు\nతేదీ: 12/06/2023",
            "extracted": {
                "survey_number": "89/2A",
                "subdivision_number": "2A",
                "khasra_khata": "74",
                "owner_name": "వెంకటేశ్వర రావు",
                "land_area": "3.20 ఎకరాలు",
                "village": "సూలూరు",
                "taluk": "సూలూరు",
                "district": "Coimbatore",
                "state": "Tamil Nadu",
                "land_classification": "మెట్ట (Dryland)",
                "document_number": "TEL-PPB-89/2A",
                "document_date": "12/06/2023"
            }
        }
    else:
        return {
            "lang": "en",
            "lang_name": "English",
            "script": "Latin",
            "raw_text": "Government of Tamil Nadu - Revenue Department\nTitle Deed / Patta Record\nSurvey No: 123/4A\nSub-Division No: 4A\nKhata No: 56\nOwner Name: K. Balasubramanian\nLand Area: 2.50 acres\nClassification: Wet / Agricultural\nVillage: Sulur\nTaluk: Sulur\nDistrict: Coimbatore\nState: Tamil Nadu\nDocument No: DOC-2023-8841\nDate: 12/05/2023",
            "extracted": {
                "survey_number": "123/4A",
                "subdivision_number": "4A",
                "khasra_khata": "56",
                "owner_name": "K. Balasubramanian",
                "land_area": "2.50 acres",
                "village": "Sulur",
                "taluk": "Sulur",
                "district": "Coimbatore",
                "state": "Tamil Nadu",
                "land_classification": "Agricultural / Wet",
                "document_number": "DOC-2023-8841",
                "document_date": "12/05/2023"
            }
        }

def process_document(filename: str, content: bytes, language: str = "auto", mode: str = "auto"):
    """Adapter for intelligence: accepts filename and raw bytes, saves to temp, runs OCR."""
    import tempfile
    ext = os.path.splitext(filename)[1] or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = process_document_for_ocr(tmp_path, language=language, mode=mode)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    return result

def process_document_for_ocr(file_path: str, language: str = "auto", mode: str = "auto", parcel_id: int = None, project_id: str = None) -> dict:
    """
    Main entry point for document OCR extraction.
    Executes real OCR (PDF text layer / Tesseract / multi-page) and structured matching.
    """
    file_p = Path(file_path)
    if not file_p.is_absolute() or not file_p.exists():
        candidates = [
            UPLOADS / file_p.name,
            ROOT / file_p,
            ROOT / "uploads" / file_p.name,
            file_p
        ]
        for cand in candidates:
            if cand.exists():
                file_p = cand
                break

    ext = file_p.suffix.lower()

    if mode and mode.lower() == "handwritten":
        return {
            "success": False,
            "message": "Selected language/handwriting model is not available in the current deployment.",
            "error_code": "HANDWRITTEN_MODEL_UNAVAILABLE"
        }

    # If physical file does not exist on disk, use synthetic demo mode
    if not file_p.exists():
        mock_data = _get_mock_multilingual_data(language, file_p.name)
        text = mock_data["raw_text"]
        detected_lang = mock_data["lang"]
        detected_script = mock_data["script"]
        lang_name = mock_data["lang_name"]
        lang_conf = 0.85
        lang_uncert = "Estimated confidence"
        ocr_engine = "Synthetic OCR / Demo Mode (Host sample record)"
        fields_raw = mock_data["extracted"]
        extracted_fields = {
            fn: {
                "value": val,
                "confidence": 0.85,
                "requires_verification": False,
                "uncertainty_label": "Estimated confidence"
            }
            for fn, val in fields_raw.items()
        }
        flat_extracted = {k: v["value"] for k, v in extracted_fields.items()}
        survey_no = flat_extracted.get("survey_number", "")
        village = flat_extracted.get("village", "")
        taluk = flat_extracted.get("taluk", "")
        district = flat_extracted.get("district", "")
        dup_info = check_duplicate_parcel(survey_no, village, taluk, district)
        match_info = match_parcel_to_document(flat_extracted, original_parcel_id=parcel_id, project_id=project_id)
        
        return {
            "success": True,
            "raw_text": text,
            "language": detected_lang,
            "language_name": lang_name,
            "script": detected_script,
            "language_confidence": lang_conf,
            "uncertainty_label": lang_uncert,
            "ocr_engine": ocr_engine,
            "ocr_mode": "synthetic",
            "is_mock_fallback": True,
            "pages_processed": 1,
            "processing_mode": mode or "auto",
            "preprocessed_image": None,
            "preprocessing_metrics": {},
            "confidence": 0.85,
            "extracted": flat_extracted,
            "detailed_extractions": extracted_fields,
            "match": match_info,
            "ocr_status": "Verification Required",
            "human_verification_required": True,
            "duplicate_detection": dup_info,
            "message": f"Synthetic demo OCR extraction complete ({lang_name} / {detected_script}). Engine: {ocr_engine}."
        }

    # Preprocess image if image format
    processed_p = file_p.parent / f"proc_{file_p.stem}.png"
    preproc_metrics = {}
    if ext in [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"]:
        preproc_metrics = preprocess_image(file_p, processed_p)
        target_ocr_path = str(processed_p) if processed_p.exists() else str(file_p)
    else:
        target_ocr_path = str(file_p)

    text, success, msg, engine_name, pages_count, is_fallback = perform_ocr(target_ocr_path, ext, target_lang=language)

    is_mock_fallback = False
    ocr_mode = "real"

    if not success and is_fallback:
        # Tesseract is not installed on host, use graceful Demo/Synthetic Mode
        is_mock_fallback = True
        ocr_mode = "synthetic"
        mock_data = _get_mock_multilingual_data(language, file_p.name)
        text = mock_data["raw_text"]
        detected_lang = mock_data["lang"]
        detected_script = mock_data["script"]
        lang_name = mock_data["lang_name"]
        lang_conf = 0.85
        lang_uncert = "Estimated confidence"
        ocr_engine = "Synthetic OCR / Demo Mode (Host OCR engine unavailable)"
        fields_raw = mock_data["extracted"]
        
        extracted_fields = {}
        for fn, val in fields_raw.items():
            extracted_fields[fn] = {
                "value": val,
                "confidence": 0.85,
                "requires_verification": False,
                "uncertainty_label": "Estimated confidence"
            }
        avg_confidence = 0.85
    elif not success:
        return {"success": False, "message": msg, "ocr_status": "Failed", "error_code": "OCR_EXECUTION_ERROR"}
    else:
        # Real OCR Succeeded!
        is_mock_fallback = False
        ocr_mode = "real"
        ocr_engine = engine_name
        script_info = detect_script_and_language(text)
        detected_lang = script_info["language"]
        detected_script = script_info["script"]
        lang_name = script_info["language_name"]
        lang_conf = script_info["confidence"]
        lang_uncert = script_info["uncertainty_label"]

        extracted_fields = extract_multilingual_fields(text, detected_lang=detected_lang)
        conf_vals = [f["confidence"] for f in extracted_fields.values() if f["value"]]
        avg_confidence = round(sum(conf_vals) / len(conf_vals), 2) if conf_vals else 0.85

    flat_extracted = {k: v["value"] for k, v in extracted_fields.items()}

    survey_no = flat_extracted.get("survey_number", "")
    village = flat_extracted.get("village", "")
    taluk = flat_extracted.get("taluk", "")
    district = flat_extracted.get("district", "")
    dup_info = check_duplicate_parcel(survey_no, village, taluk, district)
    match_info = match_parcel_to_document(flat_extracted, original_parcel_id=parcel_id, project_id=project_id)

    overall_status = "Verification Required"

    return {
        "success": True,
        "raw_text": text,
        "pages_processed": pages_count,
        "language": detected_lang,
        "language_name": lang_name,
        "script": detected_script,
        "language_confidence": lang_conf,
        "uncertainty_label": lang_uncert,
        "ocr_engine": ocr_engine,
        "ocr_mode": ocr_mode,
        "is_mock_fallback": is_mock_fallback,
        "processing_mode": mode or "auto",
        "preprocessed_image": str(processed_p.name) if processed_p.exists() else None,
        "preprocessing_metrics": preproc_metrics,
        "confidence": avg_confidence,
        "extracted": flat_extracted,
        "detailed_extractions": extracted_fields,
        "match": match_info,
        "ocr_status": overall_status,
        "human_verification_required": True,
        "duplicate_detection": dup_info,
        "message": f"Multilingual OCR processing complete ({lang_name} / {detected_script}). Engine: {ocr_engine}."
    }


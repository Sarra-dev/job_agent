import os
import re
import spacy
import textract
import docx2txt
import pytesseract
from PIL import Image
from PIL import ImageOps
from langdetect import detect
from typing import List
from pdf2image import convert_from_path

# Load spaCy model
nlp = spacy.load("en_core_web_md")

# Define known skills
KNOWN_SKILLS = [
    "python", "java", "sql", "machine learning", "react",
    "angular", "node.js", "docker", "kubernetes",
    "javascript", "django", "c++", "html", "css", "creativity" , "leadership", "critical thiniking" , "productivity"
]

def extract_text_from_file(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".pdf":
            return textract.process(file_path).decode("utf-8", errors="ignore")
        elif ext == ".docx":
            return docx2txt.process(file_path)
        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
            pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            img = Image.open(file_path).convert("L") 
            img = ImageOps.autocontrast(img)  
            custom_config = r'--oem 3 --psm 6'
            return pytesseract.image_to_string(img, config=custom_config)
        else:
            print(f"Unsupported file format: {ext}")
            return ""
    except Exception as e:
        print(f"❌ Error extracting text from {file_path}:", e)
        return ""

def extract_text_from_pdf_via_ocr(file_path: str) -> str:
    try:
        images = convert_from_path(file_path)
        text = ''
        for img in images:
            text += pytesseract.image_to_string(img)
        return text
    except Exception as e:
        print(f"❌ OCR fallback failed: {e}")
        return ""

def match_skills(text: str):
    doc = nlp(text.lower())
    skills_found = []
    for token in doc:
        for skill in KNOWN_SKILLS:
            skill_doc = nlp(skill)
            if token.similarity(skill_doc) > 0.85:
                skills_found.append(skill)
    return list(set(skills_found))

def extract_name_and_location(text: str):
    doc = nlp(text)
    name = None
    location = None
    for ent in doc.ents:
        if ent.label_ == "PERSON" and not name and len(ent.text.split()) <= 3:
            name = ent.text
        elif ent.label_ == "GPE" and not location:
            location = ent.text
    if not name:
        for line in text.splitlines():
            if line.strip() and line.strip().istitle():
                name = line.strip()
                break
    return name, location

def extract_email(text: str):
    text = text.lower()
    pattern = r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}"
    match = re.search(pattern, text)
    return match.group().strip() if match else None

def extract_phone(text: str):
    match = re.search(r"\+?\d[\d\s().-]{7,}", text)
    return match.group() if match else None

def detect_language(text: str) -> str:
    try:
        return detect(text)
    except:
        return "unknown"

def extract_experience(text: str) -> dict:
    """
    Extracts job titles from text using more flexible regex patterns.
    """
    clean_text = text.lower()
    jobs = set()

    print("\n🔍 [DEBUG] Running improved regex job title extraction...")

    # Better generic pattern: looks for 1–3 words before common roles
    pattern = r'\b(?:[a-zA-Z]+\s){0,2}(developer|engineer|designer|manager|analyst|consultant|scientist|researcher|architect|teacher|professor|intern|accountant|lawyer|cashier|sales representative|marketing manager|business analyst)\b'

    matches = re.findall(pattern, clean_text, flags=re.IGNORECASE)
    print(f"   • [DEBUG] Matches for pattern '{pattern}': {matches}")

    for match in matches:
        jobs.add(match.strip().lower())

    # Try to extract the preceding words too (e.g., "frontend developer")
    pattern2 = r'\b([a-zA-Z]+\s(?:developer|engineer|designer|manager|analyst|consultant|scientist))\b'
    matches2 = re.findall(pattern2, clean_text, flags=re.IGNORECASE)
    print(f"   • [DEBUG] Matches for extended pattern '{pattern2}': {matches2}")

    for match in matches2:
        jobs.add(match.strip().lower())

    # Still keep fallback keywords
    fallback_keywords = ["engineer", "developer", "manager", "analyst"]
    for keyword in fallback_keywords:
        if keyword in clean_text and keyword not in jobs:
            print(f"   • [DEBUG] Fallback keyword matched: {keyword}")
            jobs.add(keyword)

    print("\n✅ [DEBUG] Final extracted jobs:", jobs)
    return {"jobs": list(jobs)}




def extract_cv_info(file_path: str):
    text = extract_text_from_file(file_path)
    if not text.strip():
        return {
            "name": "Unknown",
            "email": None,
            "phone": None,
            "location": "Unknown",
            "skills": [],
            "jobs": [],
            "language": "unknown"
        }

    language = detect_language(text)
    name, location = extract_name_and_location(text)
    skills = match_skills(text)
    experience = extract_experience(text)

    print("📄 Extracted Jobs:", experience["jobs"])
   


    return {
        "name": name or "Unknown",
        "email": extract_email(text),
        "phone": extract_phone(text),
        "location": location or "Unknown",
        "skills": skills,
        "jobs": experience["jobs"],
        "language": language
    }

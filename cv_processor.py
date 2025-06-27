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
    "python", "java", "sql", "machine learning", "react", "angular", "node.js", "docker", "kubernetes"
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

def extract_experience(text: str):
    clean_text = re.sub(r'\s+', ' ', text.replace('\r', ' ').replace('\n', ' ')).strip()

    jobs = set()
    companies = set()

    doc = nlp(clean_text)
    for ent in doc.ents:
        if ent.label_ == "ORG":
            org = ent.text.strip()

            if 3 <= len(org) <= 60:
                org_lower = org.lower()
                blacklist_keywords = [
                    "university", "college", "baccalaureate", "certification", "portfolio", "project",
                    "skill", "language", "interest", "team", "website", "student", "education",
                    "training", "course", "workshop", "conference", "session", "study", "degree",
                    "research", "department", "program"
                ]
                if not any(keyword in org_lower for keyword in blacklist_keywords):
                    companies.add(org)

    job_title_patterns = [
        r'\b(?:senior|junior|lead|principal|chief|head of|director of|vice president|vp|associate|assistant)?\s*'  # level (optional)
        r'(?:software|web|mobile|frontend|front[- ]end|backend|back[- ]end|full[- ]stack|fullstack|data|machine learning|ml|ai|artificial intelligence|devops|cloud|qa|test|security|site reliability|sre|product|project|business|technical|solution|ui|ux|graphic|interaction|visual|database|system|network|it)?\s*'  # domain (optional)
        r'(?:engineer|developer|programmer|architect|designer|analyst|manager|specialist|consultant|intern|trainee|administrator|master|scientist)\b'
    ]

    for pattern in job_title_patterns:
        matches = re.findall(pattern, clean_text, flags=re.IGNORECASE)
        for match in matches:
            job_title = re.sub(r'\s+', ' ', match).strip().lower()
            if len(job_title) > 2:
                jobs.add(job_title)

    # Remove obvious false positives from jobs & companies
    job_blacklist = {'student', 'experience', 'education', 'language', 'skill', 'project', 'interest'}
    jobs = {job for job in jobs if not any(black in job for black in job_blacklist)}

    company_blacklist = {'education', 'project', 'portfolio', 'skill', 'language', 'team', 'interest', 'certification', 'training'}
    companies = {comp for comp in companies if not any(black in comp.lower() for black in company_blacklist)}



    return {
        "jobs": list(jobs) if jobs else [],
        "companies": list(companies) if companies else [],
    }




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
            "companies": [],
            "language": "unknown"
        }

    language = detect_language(text)
    name, location = extract_name_and_location(text)
    skills = match_skills(text)
    experience = extract_experience(text)

    print("📄 Extracted Jobs:", experience["jobs"])
    print("🏢 Extracted Companies:", experience["companies"])
   


    return {
        "name": name or "Unknown",
        "email": extract_email(text),
        "phone": extract_phone(text),
        "location": location or "Unknown",
        "skills": skills,
        "jobs": experience["jobs"],
        "companies": experience["companies"],
        "language": language
    }

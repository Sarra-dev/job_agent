import textract
from langdetect import detect

def extract_text_from_file(file_path: str) -> str:
    try:
        text = textract.process(file_path).decode("utf-8", errors="ignore")
        return text
    except Exception as e:
        print("❌ Error extracting text:", e)
        return ""

def detect_language(text: str) -> str:
    try:
        return detect(text)
    except:
        return "unknown"

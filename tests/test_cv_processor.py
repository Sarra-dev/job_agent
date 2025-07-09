import os
import pytest
from cv_processor import (
    extract_text_from_file,
    extract_name_and_location,
    extract_email,
    extract_phone,
    detect_language,
    match_skills,
    extract_experience,
    extract_cv_info
)

# For mocking
from unittest.mock import patch

TEST_DATA = os.path.join(os.path.dirname(__file__), "test_data")


def test_extract_text_from_txt():
    file = os.path.join(TEST_DATA, "sample.txt")
    text = extract_text_from_file(file)
    assert "test CV" in text


def test_extract_text_from_docx():
    file = os.path.join(TEST_DATA, "sample.docx")
    text = extract_text_from_file(file)
    assert "test CV" in text


def test_extract_text_from_pdf():
    file = os.path.join(TEST_DATA, "sample.pdf")
    text = extract_text_from_file(file)
    assert "test CV" in text


def test_extract_text_from_image_mocked():
    file = os.path.join(TEST_DATA, "sample.jpg")
    with patch("cv_processor.pytesseract.image_to_string") as mock_ocr:
        mock_ocr.return_value = "This is a test CV from image. Name: John Doe."
        text = extract_text_from_file(file)
        assert "test CV" in text


def test_extract_name_and_location():
    text = "John Doe lives in Berlin"
    name, location = extract_name_and_location(text)
    assert name == "John Doe"
    assert location == "Berlin"


def test_extract_email():
    text = "Please contact me at john@example.com for details."
    email = extract_email(text)
    assert email == "john@example.com"


def test_extract_phone():
    text = "You can call me at +49 123 456 789."
    phone = extract_phone(text)
    assert "+49" in phone


def test_detect_language():
    text = "This is an English text."
    assert detect_language(text) == "en"


def test_match_skills():
    text = "I have experience in Python and Machine Learning."
    skills = match_skills(text)
    assert "python" in skills
    assert any(s in skills for s in ["machine learning", "python"])



def test_extract_experience():
    text = "I worked at Google as a Senior Software Developer."
    exp = extract_experience(text)
    assert "google" in [c.lower() for c in exp["companies"]]
    assert any("software developer" in j for j in exp["jobs"])


def test_extract_cv_info():
    file = os.path.join(TEST_DATA, "sample.txt")
    result = extract_cv_info(file)
    assert result["name"] != "Unknown"
    assert result["email"]
    assert result["language"] in ["en", "de"]


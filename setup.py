from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="job_bot",  
    version="0.1.0",
    packages=find_packages(include=["jobBot", "jobBot.*"]),
    install_requires=[
        "python-telegram-bot>=20.0,<21.0",
        "httpx>=0.23.1,<0.28.0",
        "python-dotenv>=1.0.1,<2.0.0",
        "spacy>=3.7.4,<4.0.0",
        "pytesseract>=0.3.10,<0.4.0",
        "Pillow>=10.0.0,<11.0.0",
        "textract>=1.6.3,<2.0.0",
        "langdetect>=1.0.9,<2.0.0",
        "docx2txt>=0.8,<1.0.0",
        "pdf2image>=1.17.0,<2.0.0",
        "selenium>=4.0.0,<5.0.0",
    ],
    entry_points={
        "console_scripts": [
            "job_bot=job_bot.bot:main"
        ]
    },
    #author="Your Name",
    #author_email="your.email@example.com",
    description="A Telegram bot that extracts CV info, matches jobs, and auto-fills applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    #url="https://github.com/yourusername/job_bot",  
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.8",
)

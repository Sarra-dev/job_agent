# job_fetcher.py
import os
import httpx
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"

SUPPORTED_COUNTRIES = {
    "france": "fr",
    "germany": "de"
}

def get_job_level_keywords(level: str) -> List[str]:
    """Map experience levels to Adzuna-relevant keywords."""
    mapping = {
        "junior": ["junior", "entry level", "beginner"],
        "mid": ["mid", "intermediate", "3-5 years"],
        "senior": ["senior", "expert", "lead"],
        "any": []
    }
    return mapping.get(level.lower(), [])


async def fetch_jobs(
    job_title: str,
    country: str,
    city: str,
    level: str,
    max_results: int = 5
) -> List[Dict]:
    """Fetch job offers from Adzuna API."""
    country_code = country.lower()

    if not country_code:
        return []

    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        raise EnvironmentError("ADZUNA_APP_ID or ADZUNA_APP_KEY not set in environment.")

    # Only use the job title for now (omit level to avoid filtering out results)
    query = job_title

    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "results_per_page": max_results,
        "what": query,
        "where": city if city != "any" else ""
    }

    url = f"{ADZUNA_BASE_URL}/{country_code}/search/1"

    # 🔍 DEBUG PRINTS
    print(f"\n🔍 Querying Adzuna with:")
    print(f"    Country: {country_code}")
    print(f"    City: {city}")
    print(f"    Query: {query}")
    print(f"🔗 URL: {url}")
    print(f"📦 Params: {params}\n")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            return parse_adzuna_response(data)
    except Exception as e:
        print(f"[Adzuna Error] {e}")
        return []


def parse_adzuna_response(data: Dict) -> List[Dict]:
    """Convert raw Adzuna results to a clean list of job offers."""
    results = data.get("results", [])
    jobs = []

    print("📥 Adzuna API raw 'results':", results)

    for job in results:
        if not isinstance(job, dict):
            continue

        title = job.get("title", "N/A")

        # ✅ Company
        company = "Unknown"
        if isinstance(job.get("company"), dict):
            company = job["company"].get("display_name", "Unknown")

        # ✅ Location – Handle missing field entirely
        location = "Not provided"
        if "location" in job and isinstance(job["location"], dict):
            location = job["location"].get("display_name", "Not specified")

        description = job.get("description", "")
        url = job.get("redirect_url", "#")

        jobs.append({
            "title": title,
            "company": company,
            "location": location,
            "level": "N/A",
            "description": description[:500],
            "url": url
        })

    return jobs


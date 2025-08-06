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
    results = data.get("results", [])
    jobs = []

    for job in results:
        if not isinstance(job, dict):
            continue

        jobs.append({
            "id": job.get("id"),
            "title": job.get("title"),
            "company": job.get("company"),  # keep as dict!
            "location": job.get("location"),  # keep as dict!
            "description": job.get("description"),
            "redirect_url": job.get("redirect_url")
        })

    return jobs



"""Local resume parsing and evidence-based job-listing matching for Jarvis."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit


SKILL_TERMS = (
    "Power BI", "SQL", "Tableau", "Python", "Databricks", "MySQL", "PostgreSQL",
    "Azure Data Factory", "Azure Synapse", "Excel", "DAX", "Power Query",
    "XGBoost", "Data Modeling", "ETL", "SQL Server", "SSIS", "PySpark",
    "Snowflake", "AWS", "Data Visualization", "Stakeholder Management",
    "SPSS", "Quantum", "Looker", "Looker Studio", "BigQuery", "SAP",
    "Google Analytics", "Machine Learning", "R", "D2C", "SSAS",
)


def extract_resume_profile(pdf_path: str, python_path: str, extractor_path: str) -> dict:
    """Extract a selected PDF locally and return only matching-relevant profile facts."""
    completed = subprocess.run(
        [python_path, extractor_path, pdf_path], capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60, check=False,
    )
    try:
        parsed = json.loads(completed.stdout)
    except (TypeError, ValueError) as exc:
        raise ValueError("The local resume extractor returned invalid output") from exc
    if completed.returncode != 0 or not parsed.get("ok"):
        raise ValueError(str(parsed.get("error") or "The selected PDF could not be extracted locally."))
    text = str(parsed.get("text") or "")
    if not text.strip():
        raise ValueError("The selected PDF contains no extractable text")

    role_match = re.search(r"\bSeeking\s+(.+?)\s+roles?\s+where\b", text, re.IGNORECASE | re.DOTALL)
    roles = []
    if role_match:
        roles = [" ".join(part.strip(" .;\n\t").split()) for part in re.split(r"\s*/\s*|\s*,\s*|\s+or\s+", role_match.group(1)) if part.strip()]
    if not roles:
        roles = [role for role, terms in (
            ("Senior Data Analyst", ("data analyst",)),
            ("BI Analyst", ("power bi", "tableau", "business intelligence")),
            ("Power BI Engineer", ("power bi", "sql", "dashboard")),
        ) if all(term in text.lower() for term in terms)]

    years_match = re.search(r"\b(\d+(?:\.\d+)?)\s*\+?\s*years?\b", text, re.IGNORECASE)
    years = float(years_match.group(1)) if years_match else None
    top = "\n".join(text.splitlines()[:8])
    location_match = re.search(r"\b(Noida(?:,\s*NCR)?|NCR|Delhi|India)\b[^\n|]{0,35}", top, re.IGNORECASE)
    location = location_match.group(0).strip(" |,") if location_match else ""
    education_match = re.search(
        r"\b(Bachelor(?: of Technology| of Engineering)?(?:\s*\([^\n|)]*\))?\s*,?\s*[^\n|]{0,55}|B\.?Tech\.?\s*,?\s*[^\n|]{0,55})",
        text, re.IGNORECASE,
    )
    education = " ".join(education_match.group(1).split()).strip(" ,|") if education_match else ""
    skills = [skill for skill in SKILL_TERMS if re.search(r"(?<!\w)" + re.escape(skill) + r"(?!\w)", text, re.IGNORECASE)]
    return {
        "roles": roles,
        "years_experience": years,
        "location": location,
        "education": education,
        "work_arrangement_preference": "",
        "skills": skills,
        "text": text,
        "page_count": parsed.get("page_count"),
        "pages_with_text": parsed.get("pages_with_text"),
    }


def job_search_queries(profile: dict, posted_within_hours: int | None = None) -> list[str]:
    location = profile.get("location") or "India"
    roles = profile.get("roles") or ["Data Analyst", "BI Analyst"]
    primary_role = " ".join(str(roles[0]).split())
    # Search for active role pages broadly. Posting date is a ranking signal,
    # not an eligibility cutoff; older openings can still be open.
    freshness = "currently open apply"
    queries = [
        f'site:jobs.lever.co India "Data Analyst" Power BI SQL {freshness}',
        f'site:myworkdayjobs.com India ("Data Analyst" OR "BI Analyst" OR "Power BI") apply {freshness}',
        f'site:boards.greenhouse.io India ("Data Analyst" OR "BI Analyst") Power BI {freshness}',
        f'site:*.oraclecloud.com India "Data Analyst" Power BI SQL {freshness}',
        f'site:careers.smartrecruiters.com India "Data Analyst" SQL {freshness}',
        f'site:jobs.ashbyhq.com India "Data Analyst" Power BI {freshness}',
        f'"{primary_role}" ("{location}" OR India) careers "Posted Today" SQL Power BI {freshness}',
        f'("{primary_role}" OR "BI Analyst" OR "Power BI Developer") India careers apply {freshness}',
        f'site:job-boards.greenhouse.io India "Data Analyst" Power BI SQL {freshness}',
        f'India "Senior Data Analyst" ("Posted Today" OR "Posted Yesterday") careers SQL {freshness}',
    ]
    return queries


def _schema_company(record: dict) -> str:
    org = record.get("hiringOrganization", {})
    if isinstance(org, dict):
        return str(org.get("name") or "").strip()
    return str(org or "").strip()


def _schema_location(record: dict) -> str:
    locations = record.get("jobLocation") or []
    if isinstance(locations, dict):
        locations = [locations]
    values = []
    for item in locations:
        address = item.get("address", {}) if isinstance(item, dict) else {}
        if isinstance(address, dict):
            value = ", ".join(str(address.get(key)) for key in ("addressLocality", "addressRegion", "addressCountry") if address.get(key))
            if value:
                values.append(value)
    return "; ".join(values)


def _structured_salary(record: dict) -> str:
    salary = record.get("baseSalary") or record.get("estimatedSalary")
    if not isinstance(salary, dict):
        return ""
    currency = str(salary.get("currency") or "").strip()
    value = salary.get("value")
    if isinstance(value, dict):
        low = value.get("minValue")
        high = value.get("maxValue")
        amount = f"{low}–{high}" if low is not None and high is not None else value.get("value")
        unit = str(value.get("unitText") or "").strip()
    else:
        amount, unit = value, ""
    if amount is None:
        return ""
    return " ".join(part for part in (currency, str(amount), unit) if part)


def _first(pattern: str, text: str, flags=re.IGNORECASE) -> str:
    found = re.search(pattern, text, flags)
    return found.group(1).strip(" \t|,.;") if found else ""


def _expired(page: dict, text: str, today: date) -> bool:
    if page.get("posting_available") is False:
        return True
    if re.search(r"\b(no longer accepting applications|job posting (?:is )?closed|position has been filled|job is no longer available|posting expired)\b", text, re.IGNORECASE):
        return True
    record = page.get("structured_job") or {}
    through = str(record.get("validThrough") or "")
    if through:
        try:
            return datetime.fromisoformat(through.replace("Z", "+00:00")).date() < today
        except ValueError:
            pass
    text = text + "\n" + str(record.get("description") or "")
    deadline = _first(r"(?:end date|apply before|deadline|applications? close(?:s)?(?: on)?|closing date)\s*:?\s*((?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}|\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}))", text)
    for fmt in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y", "%d %B %Y", "%d %b %Y"):
        if deadline:
            try:
                return datetime.strptime(deadline, fmt).date() < today
            except ValueError:
                continue
    return False


def _posted_datetime(page: dict, text: str, now: datetime | None = None) -> datetime | None:
    """Parse a page's posting date or an explicit relative label anchored to retrieval."""
    now = now or datetime.now().astimezone()
    if now.tzinfo is None:
        now = now.astimezone()
    record = page.get("structured_job") or {}
    raw = str(record.get("datePosted") or page.get("search_date") or "").strip()
    relative_match = re.search(
        r"\bposted\s+(today|yesterday|\d+\s+(?:hours?|hrs?|days?)\s+ago)\b",
        text,
        re.IGNORECASE,
    )
    relative = raw or (relative_match.group(1) if relative_match else "")
    relative = relative.lower().replace("posted", "").strip()
    if relative == "today":
        return datetime.combine(now.date(), time.min).astimezone()
    if relative == "yesterday":
        return datetime.combine(now.date() - timedelta(days=1), time.min).astimezone()
    ago = re.fullmatch(r"(\d+)\s*(hours?|hrs?|days?)\s+ago", relative)
    if ago:
        amount = int(ago.group(1))
        unit = ago.group(2)
        if amount > 30:
            return None
        return now - (timedelta(days=amount) if unit.startswith("day") else timedelta(hours=amount))
    if not raw:
        raw = _first(r"\b(?:date posted|posted on|published)\s*:?\s*((?:\d{4}-\d{2}-\d{2}(?:[T ][^\s|]+)?|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}))", text)
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        parsed = None
    if parsed is None:
        for fmt in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"):
            try:
                parsed_date = datetime.strptime(raw, fmt).date()
                parsed = datetime.combine(parsed_date, time.min).astimezone()
                break
            except ValueError:
                continue
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    elif parsed.time() == time.min:
        # Date-only employer metadata is interpreted as local midnight so a strict
        # rolling window does not accidentally include an older calendar day.
        parsed = datetime.combine(parsed.date(), time.min).astimezone()
    return parsed


def _skills_in(text: str) -> list[str]:
    return [skill for skill in SKILL_TERMS if re.search(r"(?<!\w)" + re.escape(skill) + r"(?!\w)", text, re.IGNORECASE)]


def _company_from(page: dict, record: dict, title: str, text: str) -> str:
    def credible(value: str) -> bool:
        return bool(value and len(value) <= 70 and not re.search(
            r"(?:\*\*|\b(?:location|department|published|experience)\s*:)", value, re.IGNORECASE,
        ))

    company = _schema_company(record)
    if credible(company):
        return company
    company_source = page.get("snippet", "") + "\n" + text
    company = _first(r"\[([^\]]+)\]\s*\(/company/", company_source)
    if not company:
        company = _first(r"\b(?:Company|Hiring Organization|Posted By)\s*:\s*([^\n|]+)", company_source)
    if not company:
        company = _first(
            r"\bJob Application for .{2,100}?\s+at\s+([A-Z][A-Za-z0-9& .'-]{1,40})(?=\s+Back to jobs\b|[|.!\n])",
            text,
        )
    if company:
        company = company.split(",", 1)[0].strip()
        if credible(company):
            return company
    host = urlsplit(str(page.get("final_url") or page.get("url") or "")).hostname or ""
    # Greenhouse/Ashby/Lever expose the employer as the first path segment;
    # the ATS host itself is not the hiring company. Prefer this over page-title
    # fragments that sometimes contain the whole location/description block.
    if host.endswith("greenhouse.io") or host.endswith("ashbyhq.com") or host.endswith("lever.co"):
        segments = [part for part in urlsplit(str(page.get("final_url") or page.get("url") or "")).path.split("/") if part]
        reserved = {"jobs", "job", "careers", "apply", "application"}
        if segments and segments[0].lower() not in reserved:
            return segments[0].replace("-", " ").title()
    company = _first(r"\b(?:at|in|from)\s+([A-Z][A-Za-z0-9& .'-]{2,50})(?:\s*[,|·]|\s+Job\b|$)", title)
    if credible(company):
        return company
    workday_tenant = re.match(r"([a-z0-9-]+)\.wd\d+\.myworkdayjobs\.com$", host, re.IGNORECASE)
    if workday_tenant:
        return workday_tenant.group(1).replace("-", " ").title()
    keka_tenant = re.match(r"([a-z0-9-]+)\.keka\.com$", host, re.IGNORECASE)
    if keka_tenant:
        tenant = keka_tenant.group(1).replace("-", " ")
        if tenant.startswith("team") and len(tenant) > 4 and " " not in tenant:
            return "Team " + tenant[4:].title()
        return tenant.title()
    # On a verified employer URL, the registrable domain is a useful fallback
    # when the page has no JobPosting schema or explicit company label.
    if page.get("employer_detail_verified"):
        host = urlsplit(str(page.get("final_url") or page.get("url") or "")).hostname or ""
        labels = host.lower().split(".")
        brand = labels[-2] if len(labels) >= 2 else ""
        reserved = {"jobs", "careers", "job-boards", "boards", "myworkdayjobs", "oraclecloud", "smartrecruiters", "ashbyhq", "lever"}
        if brand and brand not in reserved:
            return brand.replace("-", " ").title()
    return "Unknown"


def _is_job_detail_page(page: dict) -> bool:
    record = page.get("structured_job") or {}
    if record.get("@type") == "JobPosting" or record.get("@type") == ["JobPosting"]:
        return True
    if page.get("posting_available") is not None:
        return True
    url = str(page.get("final_url") or page.get("url") or "")
    path = urlsplit(url).path.lower().rstrip("/")
    if not path:
        return False
    if any(token in path for token in ("/job-search", "/search-jobs", "-jobs-srch", "/q-", "/jobs.htm")):
        return False
    segments = [part for part in path.split("/") if part]
    if len(segments) >= 2 and segments[-1] == "jobs":
        return False
    if "company" in segments and segments[-1] in {"jobs", "careers"}:
        return False
    if "/job/" in path or "/job-listing/" in path or "/j/" in path:
        return True
    if len(segments) >= 2 and segments[-2] == "jobs" and segments[-1] not in {"search", "careers", "jobs"}:
        return True
    if page.get("employer_detail_verified") and re.search(
        r"(?:data[-_/ ]?(?:analyst|analytics)|bi[-_/ ]?analyst|business[-_/ ]?intelligence|power[-_/ ]?bi)",
        path,
        re.IGNORECASE,
    ):
        return True
    if re.search(r"/jobdetails/\d+$", path):
        return True
    if "/jobs/" in path and len(segments) >= 2 and re.search(r"\d{4,}|[a-f0-9]{8}-[a-f0-9-]{20,}", segments[-1]):
        return True
    return False


def _url_title_conflict(page: dict, title: str) -> bool:
    """Reject indexed metadata whose role disagrees with employer URL slug."""
    path = urlsplit(str(page.get("final_url") or page.get("url") or "")).path.lower()
    path = re.sub(r"[-_]+[a-z0-9]{3,}$", "", path.rsplit("/", 1)[-1])
    title_lower = title.lower()
    if "accountant" in path and not re.search(r"\baccountant\b", title_lower):
        return True
    if re.search(r"\b(?:sales|recruiter|nurse|software-engineer|software-engineer|customer-support)\b", path) and not re.search(
        r"\b(?:sales|recruiter|nurse|software engineer|customer support)\b", title_lower,
    ):
        return True
    return False


def _score(profile: dict, title: str, text: str, location: str, experience: str) -> tuple[int, list[str], list[str], list[str]]:
    candidate_skills = set(profile.get("skills", []))
    posting_skills = set(_skills_in(text))
    matched = sorted(candidate_skills & posting_skills)
    missing = sorted(posting_skills - candidate_skills)
    # Avoid giving full skill credit when a posting exposes only one or two
    # recognizable requirements. Five matched skills fill this dimension.
    skill_score = round(45 * len(matched) / max(5, len(posting_skills))) if posting_skills else 0

    title_lower = title.lower()
    if "senior data analyst" in title_lower:
        title_score = 25
    elif "data analyst" in title_lower or "bi analyst" in title_lower:
        title_score = 22
    elif "power bi" in title_lower and ("engineer" in title_lower or "developer" in title_lower):
        title_score = 20
    elif any(word in title_lower for word in ("analyst", "business intelligence", "reporting")):
        title_score = 16
    else:
        title_score = 8

    years = profile.get("years_experience")
    min_years = _first(r"(\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*\d+(?:\.\d+)?\s*(?:years?|yrs?)", experience)
    if not min_years:
        min_years = _first(r"(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)", experience)
    if years is not None and min_years:
        exp_score = 15 if years >= float(min_years) else max(0, round(15 * years / float(min_years)))
    else:
        exp_score = 8

    loc = location.lower()
    if any(token in loc for token in ("noida", "ncr", "delhi", "gurugram", "gurgaon", "remote", "india remote")):
        location_score = 10
    elif "india" in loc:
        location_score = 7
    elif not loc:
        location_score = 4
    else:
        location_score = 1
    seniority_score = 5 if any(term in title_lower for term in ("senior", "lead", "principal")) else 3

    total = min(100, title_score + skill_score + exp_score + location_score + seniority_score)
    reasons = [
        f"Role alignment: {title_score}/25 based on the resume's target roles and the posted title.",
        f"Skill overlap: {skill_score}/45; shared skills: {', '.join(matched) if matched else 'no explicit overlap found'}.",
        f"Experience fit: {exp_score}/15; resume states {years:g}+ years." if years is not None else f"Experience fit: {exp_score}/15; years are not explicit in the resume.",
        f"Location fit: {location_score}/10 for {location or 'unspecified location'}.",
    ]
    concerns = []
    if missing:
        concerns.append("Posting also mentions skills not evidenced in the resume: " + ", ".join(missing) + ".")
    if len(posting_skills) < 3:
        total = min(total, 78)
        concerns.append("The posting exposes too few matchable technical skills for a high-confidence fit score.")
    if min_years and years is not None and years < float(min_years):
        concerns.append(f"Posting's minimum experience appears to be {min_years} years; resume states {years:g}+.")
    if location_score < 7:
        concerns.append("Location or work mode may not match the resume location; verify before applying.")
    return total, reasons, concerns, sorted(posting_skills)


def _eligibility_adjustments(profile: dict, job_text: str, location: str, work_mode: str) -> tuple[int, list[str], list[str]]:
    """Deduct for material gaps and keep uncertain eligibility visible in the score."""
    resume_text = str(profile.get("text") or "").lower()
    adjustments = []
    concerns = []
    penalty = 0

    domain_terms = ("mutual fund", "investment product", "financial research", "investment research", "bfsi", "fintech")
    missing_domains = [term for term in domain_terms if term in job_text.lower() and term not in resume_text]
    if missing_domains:
        preferred = bool(re.search(r"prefer(?:ably|red)?[^.\n]{0,180}(?:" + "|".join(map(re.escape, missing_domains)) + r")", job_text, re.IGNORECASE))
        cost = 7 if preferred else 11
        penalty += cost
        if any(term in missing_domains for term in ("mutual fund", "investment product")):
            domain_label = "mutual-fund/investment-product or financial-services experience"
        else:
            domain_label = "financial-research or financial-services experience"
        concerns.append(f"Domain fit needs review: the posting mentions {domain_label}, which is not evidenced in the resume.")
        adjustments.append(f"Domain experience gap: -{cost} points.")

    education = str(profile.get("education") or "").strip()
    edu_terms = ("finance", "economics", "statistics", "data analytics")
    job_lower = job_text.lower()
    education_clauses = re.findall(
        r"[^.\n]*(?:education\s*:|educational\s+(?:background|qualification)|academic\s+qualification|degree\s+requirement)[^.\n]*",
        job_text, re.IGNORECASE,
    )
    education_requirements = [clause for clause in education_clauses if any(term in clause.lower() for term in edu_terms)]
    if education and education_requirements and not any(term in education.lower() for term in edu_terms):
        # The employer may interpret "related field" broadly; flag uncertainty rather than declaring ineligible.
        penalty += 10
        listed_fields = sorted({term for term in edu_terms if any(term in clause.lower() for clause in education_requirements)})
        concerns.append(f"Education eligibility is unclear: the posting names {', '.join(listed_fields)}; the resume lists {education}.")
        adjustments.append("Unconfirmed education-field requirement: -10 points.")

    preference = str(profile.get("work_arrangement_preference") or "").strip().lower()
    if work_mode in {"On-site", "Hybrid"} and not preference:
        penalty += 3
        concerns.append(f"The resume does not state willingness for {work_mode.lower()} work; confirm the arrangement before applying.")
        adjustments.append("Unconfirmed work-arrangement preference: -3 points.")

    return penalty, concerns, adjustments


def match_job_pages(
    profile: dict,
    pages: list[dict],
    today: date | None = None,
    max_age_hours: int | None = None,
    now: datetime | None = None,
    max_results: int = 10,
) -> tuple[list[dict], dict]:
    """Keep only destination-fetched postings; mark uncertain current status explicitly."""
    today = today or date.today()
    now = now or datetime.now().astimezone()
    if now.tzinfo is None:
        now = now.astimezone()
    jobs = []
    seen = set()
    freshness_excluded = 0
    freshness_unknown = 0
    rejected = {
        "unverified_destination": 0, "not_job_detail": 0, "irrelevant_title": 0,
        "internship": 0, "closed_or_expired": 0, "outside_freshness_window": 0,
        "posting_date_unknown": 0, "company_unknown": 0, "apply_link_unverified": 0,
        "outside_location_scope": 0, "duplicate": 0,
    }
    for page in pages:
        title = str(page.get("page_title") or page.get("title") or "").strip()
        content = str(page.get("content") or "").strip()
        snippet = str(page.get("snippet") or "").strip()
        record = page.get("structured_job") or {}
        text = "\n".join((title, content, snippet, str(record.get("description") or ""))).replace("\ufffd", "-")
        indexed_preview = bool(page.get("indexed_listing_evidence"))
        has_page_evidence = bool(content or (record.get("@type") == "JobPosting" and record.get("description")) or indexed_preview)
        destination_checked = bool(page.get("employer_detail_verified", True)) and bool(
            (page.get("http_status") == 200 and has_page_evidence)
            or (page.get("web_extract_verified") and has_page_evidence)
        )
        if not destination_checked:
            rejected["unverified_destination"] += 1
            continue
        if not _is_job_detail_page(page):
            rejected["not_job_detail"] += 1
            continue
        if (not title or len(title) > 180
                or not re.search(r"\b(data analyst|bi analyst|business intelligence|power bi|reporting analyst|data\s*&?\s*analytics|analytics analyst)\b", title, re.IGNORECASE)):
            rejected["irrelevant_title"] += 1
            continue
        if _url_title_conflict(page, title):
            rejected["irrelevant_title"] += 1
            continue
        if re.search(r"\b(intern|internship|trainee)\b", title, re.IGNORECASE):
            rejected["internship"] += 1
            continue
        if _expired(page, text, today):
            rejected["closed_or_expired"] += 1
            continue
        posting_date_on_employer_page = _posted_datetime(
            {"structured_job": record}, title + "\n" + content, now=now,
        )
        posting_date_from_index = False
        posted_at = None
        # Do not reject an opening based on its age or missing posting date.
        # Only explicit closure, expired deadline, or unavailable employer
        # application pages make a role ineligible. Date is used for ranking.
        if max_age_hours is not None:
            posted_at = posting_date_on_employer_page or _posted_datetime(page, text, now=now)
            posting_date_from_index = posting_date_on_employer_page is None and posted_at is not None
            if posted_at is None:
                freshness_unknown += 1

        company = _company_from(page, record, title, text)
        if not company or company.casefold() == "unknown":
            rejected["company_unknown"] += 1
            continue
        content_title = _first(r"^(?:#\s*)?(?:Job Title\s*:?\s*)?([^\n]+)", content[:300])
        job_title = str(record.get("title") or page.get("page_title") or title or content_title).strip()
        job_title = re.sub(r"\s+(?:Job\s+)?in\s+[^|]+$", "", job_title, flags=re.IGNORECASE).strip()
        job_title = re.sub(r"\s+at\s+[^|]+$", "", job_title, flags=re.IGNORECASE).strip()
        location_source = snippet + "\n" + content[:1800] + "\n" + str(record.get("description") or "")[:1800]
        location = _schema_location(record) or _first(
            r"\b((?:Gurugram|Gurgaon|Noida|Delhi|Bengaluru|Bangalore|Mumbai|Pune|Hyderabad|Chennai|Kolkata|Ahmedabad|Jaipur|Kochi|Mohali|Chandigarh|Lucknow|Indore|Coimbatore)"
            r"(?:,\s*(?:Haryana|Karnataka|Maharashtra|Telangana|Tamil Nadu|West Bengal|Gujarat|Rajasthan|Kerala|Punjab|Uttar Pradesh|Madhya Pradesh|Delhi))?"
            r"(?:,\s*India)?)\b",
            location_source,
        )
        if not location:
            location = _first(r"\bLocation\s*:?\s*([^\n|.!]{2,80}?)(?=\s+(?:Experience|Department|Employment Type|Work Mode)\s*:|\s{2,}|$)", location_source)
        if not location:
            location = "Noida, India" if re.search(r"\bNoida\b", text, re.IGNORECASE) else "India" if re.search(r"\bIndia\b", text, re.IGNORECASE) else ""
        profile_location = str(profile.get("location") or "").lower()
        outside_country = bool(re.search(
            r"\b(?:united states|u\.s\.a?\.?|canada|united kingdom|u\.k\.?|australia|new zealand|singapore|germany|france|ireland|netherlands|switzerland|spain|portugal|poland|sweden|norway|denmark|finland|japan|south korea|china|brazil|mexico|philippines|malaysia|indonesia|thailand|uae|united arab emirates)\b",
            location,
            re.IGNORECASE,
        ))
        if "india" in profile_location and outside_country and "india" not in location.lower():
            rejected["outside_location_scope"] += 1
            continue
        work_mode_text = str(record.get("jobLocationType") or "")
        if not work_mode_text:
            work_mode_text = _first(r"(?:work mode|work arrangement)\s*:?\s*([^\n|]{1,40})", text)
        if not work_mode_text:
            work_mode_text = _first(r"\b(remote|hybrid|work from (?:the )?office|in office|in-office|on-site|onsite)\b", text[:6000])
        work_mode = "Remote" if re.search(r"remote", work_mode_text, re.IGNORECASE) else "Hybrid" if re.search(r"hybrid", work_mode_text, re.IGNORECASE) else "On-site" if re.search(r"(on[- ]site|onsite|in[- ]office|in office|work from (?:the )?office)", work_mode_text, re.IGNORECASE) else "Unspecified"
        experience_source = (text + "\n" + str(record.get("description") or "")).replace("\ufffd", "-")
        experience = _first(r"\b(\d+(?:\.\d+)?\s*(?:-|–|—|to)\s*\d+(?:\.\d+)?\s*(?:years?|yrs?)|\d+(?:\.\d+)?\s*\+\s*(?:years?|yrs?))", experience_source)
        if not experience:
            experience = _first(r"(?:experience|required experience|years of experience)\s*:?\s*([^\n.]{1,70}(?:years?|yrs?)[^\n.]*)", experience_source)
        posted = str(record.get("datePosted") or _first(r"\bPublished\s*:?\s*(\d{4}-\d{2}-\d{2})", title + "\n" + content) or page.get("search_date") or (posted_at.date().isoformat() if posted_at is not None else "Not stated"))
        if posted != "Not stated":
            try:
                if date.fromisoformat(posted[:10]) > today:
                    concerns_date = "Posting date is in the future; date needs confirmation."
                else:
                    concerns_date = ""
            except ValueError:
                concerns_date = ""
        else:
            concerns_date = ""

        apply_links = page.get("apply_links") or []
        apply_url = next((str(item.get("url")) for item in apply_links if "https://" in str(item.get("url", ""))), "")
        direct_apply = bool(record.get("directApply"))
        employer_page_verified = bool(page.get("employer_detail_verified", True))
        verified_apply = employer_page_verified and (
            page.get("posting_available") is True or direct_apply or bool(apply_url)
            or bool(re.search(r"\bApply(?: Now)?\b", content, re.IGNORECASE))
        )
        apply_signal = verified_apply or indexed_preview
        if not apply_url and (page.get("posting_available") is True or direct_apply or verified_apply or indexed_preview):
            apply_url = str(page.get("final_url") or page.get("url") or "")
        if not apply_signal:
            rejected["apply_link_unverified"] += 1
            continue
        parsed_url = urlsplit(apply_url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            rejected["apply_link_unverified"] += 1
            continue

        if indexed_preview and (not verified_apply or posting_date_from_index):
            status = "provisional; search-index date/details need employer confirmation"
        elif apply_signal:
            status = "application page active"
        else:
            status = "unverified"
        scoring_text = str(record.get("description") or content[:6000] or snippet)
        score, reasons, concerns, required_skills = _score(profile, job_title, scoring_text, location, experience)
        eligibility_penalty, eligibility_concerns, score_adjustments = _eligibility_adjustments(profile, text + "\n" + scoring_text, location, work_mode)
        score = max(0, score - eligibility_penalty)
        concerns.extend(eligibility_concerns)
        reasons.extend(score_adjustments)
        min_required = _first(r"(\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*\d+(?:\.\d+)?\s*(?:years?|yrs?)", experience)
        if not min_required:
            min_required = _first(r"(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)", experience)
        profile_years = profile.get("years_experience")
        if profile_years is not None and min_required and float(min_required) >= profile_years + 3:
            score = min(score, 55)
            concerns.append(f"The role appears to require at least {min_required} years; the resume states {profile_years:g}+.")
        if re.search(r"\b(noida|greater noida|ncr|delhi|gurugram|gurgaon|remote)\b", location, re.IGNORECASE) is False and location:
            score = min(score, 68)
        if concerns_date:
            concerns.append(concerns_date)
        if status != "application page active":
            concerns.append("Employer job URL responded, but the search-index posting date/details or application status need confirmation.")
        elif posting_date_from_index:
            concerns.append("Posting date was supplied by the search index, not stated on the employer page; verify recency before applying.")
        key = (company.casefold(), job_title.casefold())
        if key in seen:
            rejected["duplicate"] += 1
            continue
        seen.add(key)
        jobs.append({
            "title": job_title,
            "company": company,
            "url": apply_url,
            "source": urlsplit(str(page.get("final_url") or page.get("url", ""))).netloc,
            "location": location or "Not stated",
            "work_mode": work_mode,
            "posted_date": posted,
            "experience_requirement": experience or "Not stated",
            "required_skills": required_skills,
            "preferred_skills": [],
            "match_score": f"{score}/100",
            "match_reasons": reasons,
            "concerns": concerns,
            "salary": _structured_salary(record) or _first(r"\b(?:salary|compensation)\s*:\s*([^\n|.;]{1,80})", text[:1800]) or "Not stated",
            "status": status,
            "destination_url": str(page.get("final_url") or page.get("url") or ""),
        })
    def posted_ordinal(item):
        try:
            return date.fromisoformat(str(item.get("posted_date") or "")[:10]).toordinal()
        except ValueError:
            return 0

    jobs.sort(key=lambda item: (
        item["status"] == "application page active",
        int(item["match_score"].split("/", 1)[0]),
        posted_ordinal(item),
    ), reverse=True)
    total_matching = len(jobs)
    jobs = jobs[:max(0, max_results)]
    summary = {
        "roles": profile.get("roles", []),
        "years_experience": profile.get("years_experience"),
        "location": profile.get("location"),
        "skills": profile.get("skills", []),
        "extracted_pages": len(pages),
        "matching_before_limit": total_matching,
        "returned": len(jobs),
        "verified_destinations": sum(1 for page in pages if (page.get("http_status") == 200 and (page.get("content") or ((page.get("structured_job") or {}).get("@type") == "JobPosting" and (page.get("structured_job") or {}).get("description")) or page.get("indexed_listing_evidence"))) or (page.get("web_extract_verified") and page.get("content"))),
        "freshness_excluded": freshness_excluded,
        "freshness_unknown": freshness_unknown,
        "rejected": rejected,
    }
    return jobs, summary

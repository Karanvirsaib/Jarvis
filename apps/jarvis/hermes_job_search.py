"""Use Hermes' configured web tools for Jarvis' deterministic resume job workflow."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
import json
import re
import sys
from urllib.parse import urljoin, urlsplit


def _candidate_rank(item: dict) -> tuple[int, int, int, int]:
    """Prefer relevant, individual employer/ATS vacancy pages over search hubs."""
    parsed = urlsplit(str(item.get("url") or ""))
    host = (parsed.hostname or "").lower()
    path = parsed.path.lower().rstrip("/")
    title = str(item.get("title") or "").lower()
    search_text = " ".join((title, str(item.get("snippet") or ""), str(item.get("search_date") or ""))).lower()
    recent = bool(str(item.get("search_date") or "").strip()) or bool(re.search(
        r"\b(?:posted\s+(?:today|yesterday|\d+\s+(?:hours?|hrs?|days?)\s+ago)|published\s+today)\b",
        search_text,
    ))
    relevant = bool(re.search(
        r"\b(data analyst|bi analyst|business intelligence|power bi|reporting analyst|data\s*&?\s*analytics)\b",
        title,
    ))
    segments = [part for part in path.split("/") if part]
    hub = bool(re.search(r"(?:search|job-search|jobs-in-|job-alert|careers/?$)", path))
    detail = bool(re.search(r"/(?:job|jobs|jobdetails|job-listing)/[^/]+$", path)) and not hub
    if host.endswith("lever.co"):
        detail = len(segments) >= 2 and segments[-1] not in {"jobs", "careers"}
    elif host.endswith("greenhouse.io"):
        detail = len(segments) >= 3 and segments[-2] == "jobs"
    elif host.endswith("myworkdayjobs.com"):
        detail = "job" in segments and segments[-1] not in {"job", "jobs"}
    elif host.endswith("smartrecruiters.com"):
        detail = len(segments) >= 2 and segments[-1] not in {"jobs", "careers"}
    elif host.endswith("ashbyhq.com"):
        detail = len(segments) >= 2 and segments[-1] not in {"jobs", "careers"}
    elif "oraclecloud.com" in host:
        detail = "job" in segments and segments[-1] not in {"job", "jobs"}
    ats = any(host.endswith(domain) for domain in (
        "lever.co", "greenhouse.io", "myworkdayjobs.com", "smartrecruiters.com", "ashbyhq.com",
    )) or "oraclecloud.com" in host
    return (int(_trusted_job_page(str(item.get("url") or ""))), int(recent), int(relevant), int(detail or ats))


def _trusted_job_page(url: str) -> bool:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path.lower()
    segments = [part for part in path.split("/") if part]
    if host.endswith("greenhouse.io"):
        return len(segments) >= 3 and segments[-2] == "jobs"
    if host.endswith("lever.co") or host.endswith("smartrecruiters.com") or host.endswith("ashbyhq.com"):
        return len(segments) >= 2 and segments[-1] not in {"jobs", "careers"}
    if host.endswith("myworkdayjobs.com") or "oraclecloud.com" in host:
        return "job" in segments and segments[-1] not in {"job", "jobs"}
    return (
        host.startswith("careers.")
        or ("/careers/" in path and re.search(r"/(?:job|jobs|jobdetails)/[^/]+", path) is not None)
    )


class _PageParser(HTMLParser):
    """Extract ordinary public page text and visible Apply links; no browser/login bypass."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.links = []
        self.headings = []
        self._active_heading = None
        self._active_link = None
        self._hidden_depth = 0
        self._script_jsonld = False
        self.jsonld = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style", "noscript", "svg"}:
            self._hidden_depth += 1
            self._script_jsonld = tag == "script" and "ld+json" in attrs.get("type", "").lower()
            return
        if tag == "a" and attrs.get("href"):
            self.links.append({"href": attrs["href"], "text": ""})
            self._active_link = self.links[-1]
        if tag in {"h1", "h2"}:
            self._active_heading = {"tag": tag, "text": ""}

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self._hidden_depth:
            self._hidden_depth -= 1
            self._script_jsonld = False
        if tag == "a":
            self._active_link = None
        if tag in {"h1", "h2"} and self._active_heading is not None:
            if self._active_heading["text"].strip():
                self.headings.append(self._active_heading["text"].strip())
            self._active_heading = None

    def handle_data(self, data):
        value = " ".join(data.split())
        if not value:
            return
        if self._hidden_depth:
            if self._script_jsonld:
                self.jsonld.append(value)
            return
        self.parts.append(value)
        if self._active_heading is not None:
            self._active_heading["text"] += " " + value
        if self._active_link is not None:
            self._active_link["text"] = (self._active_link["text"] + " " + value).strip()


def _public_http_fallback(url: str) -> dict:
    """Fetch a public page normally. Respect HTTP/TLS failures and access restrictions."""
    import requests

    response = requests.get(
        url, timeout=6, allow_redirects=True,
        headers={"User-Agent": "JarvisLocalJobVerifier/1.0 (public listing check)"},
    )
    result = {"http_status": response.status_code, "final_url": response.url, "content": "", "page_title": "", "apply_links": [], "structured_job": {}, "posting_available": None}
    if response.status_code < 200 or response.status_code >= 300:
        result["extract_error"] = f"HTTP {response.status_code}"
        return result
    parser = _PageParser()
    parser.feed(response.text[:2_000_000])
    result["content"] = " ".join(parser.parts)[:8_000]
    result["page_title"] = next((heading for heading in parser.headings if heading), "")
    availability = __import__("re").search(r"postingAvailable\s*:\s*(true|false)", response.text, __import__("re").IGNORECASE)
    if availability:
        result["posting_available"] = availability.group(1).lower() == "true"
    result["apply_links"] = [
        {"text": item["text"][:120], "url": urljoin(response.url, item["href"])}
        for item in parser.links
        if "apply" in item["text"].lower() and item["href"].startswith(("/", "https://"))
    ][:8]
    for raw in parser.jsonld:
        try:
            payload = json.loads(raw)
        except ValueError:
            continue
        records = payload if isinstance(payload, list) else [payload]
        for record in records:
            if isinstance(record, dict) and (record.get("@type") == "JobPosting" or record.get("@type") == ["JobPosting"]):
                result["structured_job"] = record
                break
        if result["structured_job"]:
            break
    return result


def main() -> int:
    try:
        request = json.load(sys.stdin)
        queries = request.get("queries")
        if not isinstance(queries, list) or not queries or len(queries) > 10:
            raise ValueError("Expected one to ten search queries")

        from tools.web_tools import web_search_tool

        discovered: dict[str, dict] = {}
        search_errors = []
        for query in queries:
            raw = web_search_tool(str(query)[:400], limit=8)
            try:
                result = json.loads(raw)
            except (TypeError, ValueError):
                search_errors.append({"query": str(query), "error": "Search returned unreadable data"})
                continue
            if not result.get("success"):
                search_errors.append({"query": str(query), "error": str(result.get("error", "Search failed"))[:300]})
                continue
            rows = ((result.get("data") or {}).get("web") or [])
            for item in rows:
                if not isinstance(item, dict):
                    continue
                url = str(item.get("url", "")).strip()
                parsed = urlsplit(url)
                if parsed.scheme != "https" or not parsed.netloc:
                    continue
                key = url.split("#", 1)[0].rstrip("/").lower()
                if key and key not in discovered:
                    discovered[key] = {
                        "url": url,
                        "title": str(item.get("title", ""))[:300],
                        "snippet": str(item.get("description", ""))[:2500],
                        "search_date": str(item.get("published_date", ""))[:100],
                    }

        # Search providers often return generic list pages before individual jobs.
        # Rank likely vacancy pages before generic hubs, then verify a bounded set
        # with ordinary HTTPS fetches. Relative dates in snippets can rank candidates,
        # but they only create a provisional lead when the employer URL responds.
        candidates = sorted(discovered.values(), key=_candidate_rank, reverse=True)[:70]
        extracted = []
        if candidates:
            fallbacks = {}
            def fetch_safely(item):
                try:
                    primary = _public_http_fallback(item["url"])
                    primary["discovery_url"] = item["url"]
                    for link in (primary.get("apply_links") or [])[:2]:
                        link_url = str(link.get("url") or "")
                        if not link_url.startswith("https://"):
                            continue
                        try:
                            employer = _public_http_fallback(link_url)
                        except Exception:
                            continue
                        employer_text = " ".join((employer.get("page_title") or "", employer.get("content") or ""))
                        is_job_detail = bool(
                            employer.get("http_status") == 200
                            and len(employer_text) > 200
                            and re.search(r"\b(data analyst|bi analyst|business intelligence|power bi|reporting analyst|data\s*&?\s*analytics)\b", employer_text, re.IGNORECASE)
                        )
                        if is_job_detail:
                            employer["discovery_url"] = item["url"]
                            employer["discovered_apply_url"] = link_url
                            employer["discovered_apply_text"] = str(link.get("text") or "Apply")[:120]
                            employer["search_index_preview"] = item.get("snippet", "")
                            employer["employer_detail_verified"] = True
                            return item["url"], employer
                    final_url = str(primary.get("final_url") or item["url"])
                    primary["employer_detail_verified"] = _trusted_job_page(item["url"]) or _trusted_job_page(final_url)
                    return item["url"], primary
                except Exception as exc:
                    return item["url"], {"extract_error": f"Public fetch failed: {type(exc).__name__}"}
            with ThreadPoolExecutor(max_workers=10) as pool:
                for url, fetched in pool.map(fetch_safely, candidates):
                    fallbacks[url.rstrip("/").lower()] = fetched
            for candidate in candidates:
                http_result = fallbacks.get(candidate["url"].rstrip("/").lower(), {})
                content = str(http_result.get("content") or "")[:8_000]
                structured = http_result.get("structured_job") or {}
                http_apply_links = http_result.get("apply_links") or []
                if http_result.get("discovered_apply_url"):
                    http_apply_links = [{
                        "text": http_result.get("discovered_apply_text") or "Apply",
                        "url": http_result["discovered_apply_url"],
                    }, *http_apply_links]
                used_http = bool(http_result.get("http_status") == 200 and content)
                employer_detail_verified = bool(http_result.get("employer_detail_verified"))
                if not employer_detail_verified:
                    http_apply_links = []
                extracted.append({
                    **candidate,
                    "title": str(http_result.get("page_title") or structured.get("title") or candidate["title"])[:300],
                    "page_title": str(http_result.get("page_title") or "")[:300],
                    "content": content,
                    "extract_error": str(http_result.get("extract_error") or "")[:300],
                    "http_status": http_result.get("http_status"),
                    "posting_available": http_result.get("posting_available"),
                    "final_url": http_result.get("final_url") or candidate["url"],
                    "apply_links": http_apply_links,
                    "structured_job": structured,
                    "http_verified": used_http,
                    "employer_detail_verified": employer_detail_verified,
                    "web_extract_verified": False,
                    "indexed_listing_evidence": bool(
                        used_http and employer_detail_verified and _candidate_rank(candidate)[1]
                        and len(candidate.get("snippet", "")) >= 160
                    ),
                })

        json.dump({
            "searches_completed": len(queries) - len(search_errors),
            "search_errors": search_errors,
            "discovered_count": len(discovered),
            "pages": extracted,
        }, sys.stdout, ensure_ascii=False)
        return 0
    except Exception as exc:
        json.dump({"error": f"Web workflow failed: {type(exc).__name__}: {str(exc)[:300]}"}, sys.stdout)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

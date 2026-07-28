"""Recruiter relevance scoring."""

from __future__ import annotations

from typing import Any

from .utils import compact_whitespace

ROLE_RULES = [
    ("technical recruiter", 100, "technical recruiter role matches the target outreach path"),
    ("senior swe recruiter", 95, "senior SWE recruiter role is close to the target role"),
    ("software recruiter", 95, "software recruiter role is close to the target role"),
    ("engineering recruiter", 95, "engineering recruiter role is close to the target role"),
    ("engineering manager", 90, "engineering manager may influence hiring for engineering roles"),
    ("hiring manager", 88, "hiring manager may own the role or team"),
    ("university recruiter", 80, "university recruiter can be relevant for student or new-grad pipelines"),
    ("talent acquisition", 78, "talent acquisition role is relevant but less specific than technical recruiting"),
    ("people partner", 58, "people partner is adjacent to recruiting"),
    ("hr generalist", 50, "HR generalist is less specific to role-based recruiting"),
]

AREA_KEYWORDS = {
    "software": ["software", "swe", "backend", "frontend", "full stack", "developer"],
    "data": ["data", "analytics", "analyst", "scientist", "machine learning", "ml", "ai"],
    "engineering": ["engineering", "engineer", "platform", "infrastructure"],
}


def rank_recruiter(profile: dict[str, Any], company: str = "", job_title: str = "", location: str = "") -> dict[str, Any]:
    role = compact_whitespace(str(profile.get("role", "")))
    searchable = " ".join(
        compact_whitespace(str(profile.get(field, ""))).lower()
        for field in ["role", "team", "experience", "hiring_area", "source_url", "linkedin_url"]
    )

    base_score, reasons = _base_score(role.lower(), searchable)
    score = base_score

    company = compact_whitespace(company)
    if company and company.lower() in searchable:
        score += 4
        reasons.append(f"mentions {company}")

    matched_area = _matched_area(job_title, searchable)
    if matched_area:
        score += 5
        reasons.append(f"matches {matched_area} hiring area from the job title")

    location = compact_whitespace(location)
    profile_location = compact_whitespace(str(profile.get("location", "")))
    if location and profile_location and location.lower() in profile_location.lower():
        score += 3
        reasons.append(f"location overlaps with {location}")

    if compact_whitespace(str(profile.get("public_email", ""))):
        score += 2
        reasons.append("has a public email source")

    if compact_whitespace(str(profile.get("linkedin_url", ""))):
        score += 1
        reasons.append("has a public LinkedIn URL")

    if not compact_whitespace(str(profile.get("name", ""))):
        score -= 10
        reasons.append("missing recruiter name")

    score = max(0, min(100, score))
    return {
        "profile": profile,
        "score": score,
        "score_explanation": "; ".join(reasons),
    }


def rank_recruiters(recruiters: list[dict[str, Any]], company: str = "", job_title: str = "", location: str = "") -> list[dict[str, Any]]:
    ranked = [rank_recruiter(recruiter, company, job_title, location) for recruiter in recruiters]
    return sorted(ranked, key=lambda item: item["score"], reverse=True)


def _base_score(role: str, searchable: str) -> tuple[int, list[str]]:
    for token, score, reason in ROLE_RULES:
        if token in role or token in searchable:
            return score, [reason]
    if "recruiter" in role or "recruiter" in searchable:
        return 70, ["recruiter role is relevant but not clearly technical"]
    if "manager" in role or "manager" in searchable:
        return 65, ["manager role may be adjacent to hiring"]
    return 40, ["role is weakly related to recruiting or hiring"]


def _matched_area(job_title: str, searchable: str) -> str:
    lowered_title = compact_whitespace(job_title).lower()
    for area, keywords in AREA_KEYWORDS.items():
        if any(keyword in lowered_title for keyword in keywords) and any(keyword in searchable for keyword in keywords):
            return area
    return ""


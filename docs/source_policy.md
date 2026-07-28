# Source Policy

This project is designed to collect only public information or information the user is authorized to access.

Allowed default sources:

- Confirmation and reply emails from the user's own inbox
- Company about, team, careers, blog, and press pages
- Public GitHub organization pages
- Public conference or speaker pages
- Public search results from self-hosted SearXNG, DuckDuckGo, or an authorized free API
- User-provided files such as resumes, cover letters, notes, and portfolio pages

Rules for scraping:

- Check robots.txt when crawling websites.
- Respect website terms of service.
- Do not bypass login walls, paywalls, rate limits, or access controls.
- Do not infer private email addresses.
- Optional APIs such as Hunter, Apollo, or RocketReach are disabled unless the user supplies authorized keys.


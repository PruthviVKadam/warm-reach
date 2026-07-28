# Recruiter Research Prompt

Given a company, job title, and location, extract recruiter or hiring-manager candidates from public search and crawl results.

Return only valid JSON:

```json
{
  "recruiters": [
    {
      "name": "",
      "role": "",
      "location": "",
      "public_email": "",
      "linkedin_url": "",
      "team": "",
      "experience": "",
      "hiring_area": "",
      "source_url": ""
    }
  ]
}
```

Rules:

- Use only public information or sources the user is authorized to access.
- Respect robots.txt and site terms.
- Prefer recruiting, talent acquisition, engineering management, hiring manager, and university recruiting roles.
- Do not infer private emails.
- Leave fields blank when the source does not support them.


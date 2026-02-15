# RoleRadar | 2 Fast 2 MCP Hackathon

This repository contains **RoleRadar**, Team **CanTin**'s MCP setup for building agentic workflows across **Archestra** and **n8n**.

The project exposes multiple FastMCP servers that can be wired into orchestration layers to:

*   search and summarize jobs,
*   read and tailor resumes,
*   generate resume HTML previews,
*   score resume-job fit using skills + semantic similarity,
*   send notifications by email.

## What This Codebase Does

At a high level, the system composes 3 MCP servers:

1.  `server.py` (`simple-python-mcp`, port `8001`)

*   General utilities for resume workflows.
*   Tools include:
    *   `hello(name)`
    *   `get_time()`
    *   `send_mail(receiver_email, subject, content)`
    *   `read_resume(path)` (supports `.html/.htm/.pdf`)
    *   `generate_resume(data)` (renders resume HTML from template and hosts temporary preview URL)
*   Includes:
    *   MCP resource: `time://now`
    *   MCP prompt: `greeting_prompt`

1.  `job_server.py` (`JobSpy-Search-Pro`, port `8002`)

*   Job discovery MCP powered by `python-jobspy`.
*   Tool:
    *   `search_jobs(...)` with filters (location, job type, recency, remote, salary, distance)
*   Resource:
    *   `jobs://latest-summary` (markdown table summary of last query)

1.  `fit_score/fit_scoring.py` (`fit-scoring-mcp`, port `8085`)

*   Resume to JD scoring server.
*   Hybrid scoring:
    *   skill match score (using `fit_score/skills.json` synonym library)
    *   experience score (years detection)
    *   semantic similarity score (SentenceTransformers + cosine similarity)
*   Tools:
    *   `score_resume_batch(resume, jd_text_list)`
    *   `get_skill_library()`
*   Writes outputs to `fit_score/batch_results.json`.

## Archestra + n8n MCP Usage

This repo is designed so Archestra and n8n can both call the same MCP surface over HTTP.

### Server Endpoints

*   `http://127.0.0.1:8001/` -> resume utility server
*   `http://127.0.0.1:8002/` -> job search server
*   `http://127.0.0.1:8085/` -> fit scoring server

All servers use FastMCP with `transport="streamable-http"`.

### Typical Flow (Orchestrated in Archestra/n8n)

1.  Fetch jobs from `job_server.py` using `search_jobs`.
2.  Read candidate resume text using `read_resume`.
3.  Score resume against one or more JDs via `score_resume_batch`.
4.  Create tailored resume JSON through an agent prompt (`prompts.json`).
5.  Render final resume with `generate_resume` and return preview URL.
6.  Optionally notify user/recruiter through `send_mail`.

## Project Structure

*   `server.py` -> MCP server for resume ops + notifications
*   `job_server.py` -> MCP server for job search and job summary resource
*   `fit_score/fit_scoring.py` -> MCP server for fit scoring
*   `fit_score/skills.json` -> skill synonym/normalization library
*   `fit_score/batch_results.json` -> persisted scoring output
*   `resume.html` -> Jinja template used for generated resumes
*   `generated/my_resume.html` -> generated output sample
*   `prompts.json` -> agent role/system prompt presets
*   `notifier.py` -> SMTP email helper
*   `config.ini` -> local email configuration

## Local Setup

### 1\. Create and activate virtual environment

```
python3 -m venv .venv
source .venv/bin/activate
```

### 2\. Install dependencies

```
pip install fastmcp jinja2 pypdf pandas python-jobspy sentence-transformers scikit-learn tabulate
```

### 3\. (Optional) Download and cache embedding model locally

```
python fit_score/model.py
```

This saves `intfloat/e5-base-v2` into `./models/e5-base-v2/`.

### 4\. Configure email settings

Update `config.ini` for SMTP credentials used by `send_mail`.

### 5\. Run MCP servers (separate terminals)

```
python server.py
python job_server.py
python fit_score/fit_scoring.py
```

## Quick Sanity Test Ideas

*   Call `search_jobs("devops engineer", "USA")` and inspect output JSON.
*   Call `read_resume("./resume.html")`.
*   Call `score_resume_batch(resume_text, [jd_text])` with sample JD(s).
*   Call `generate_resume(data)` and open returned localhost preview URL.
*   Call `jobs://latest-summary` resource after a job search.

## Prompt Packs

`prompts.json` includes starter configurations for:

*   `jobsy` (job fetch + description extraction workflow)
*   `Resume Suggestions Agent`
*   `Resume Creator Agent`

These are useful to quickly bootstrap Archestra/n8n agent behavior and output format contracts.

## Cool Additions Worth Building Next

1.  Add a `docker-compose.yml` to run all MCP servers with one command.
2.  Add authentication/rate limits for exposed MCP endpoints.
3.  Move secrets out of `config.ini` into environment variables + `.env.example`.
4.  Add JSON schemas for tool input/output validation.
5.  Add observability: structured logs, request IDs, latency metrics.
6.  Add retry/backoff wrappers for JobSpy/network-dependent operations.
7.  Add a PDF export tool for generated resumes.
8.  Add skill-gap recommendations from missing skills in fit scoring.
9.  Add unit/integration tests with mocked MCP calls.
10.  Add CI pipeline for lint/test/check on pull requests.
11.  Add n8n workflow export (`.json`) and Archestra flow diagrams to this repo.
12.  Add leaderboard mode for hackathon demos (top matching jobs per resume).

## Security Notes

*   Do not commit real credentials in `config.ini`.
*   Prefer environment-based secrets for SMTP and API tokens.
*   Sanitize user-provided paths before reading local files in production deployments.

## Team

Built for **2 Fast 2 MCP Hackathon** by **Team CanTin**.
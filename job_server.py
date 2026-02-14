import json
import pandas as pd
from datetime import date, datetime
from typing import Optional
from fastmcp import FastMCP
from jobspy import scrape_jobs

# Initialize FastMCP server
mcp = FastMCP("JobSpy-Search-Pro")

# Global storage for the latest search results
latest_search_df = pd.DataFrame()


def date_serializer(obj):
    """Handles JSON serialization for date objects."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


@mcp.tool()
def search_jobs(
        search_term: str,
        location: str = "USA",
        results_wanted: int = 10,
        hours_old: int = 72,
        job_type: Optional[str] = None,  # Options: fulltime, parttime, internship, contract
        is_remote: bool = False,
        distance: int = 50,
        min_salary: Optional[int] = None,
        proxies: Optional[list[str]] = None
) -> str:
    """
    Advanced search for job listings with filtering.

    :param job_type: Filter by 'fulltime', 'parttime', 'internship', or 'contract'.
    :param is_remote: Set to True to search for remote positions.
    :param distance: Radius in miles for the search.
    :param min_salary: Local filter to only show jobs above this annual salary.
    """
    global latest_search_df
    try:
        df = scrape_jobs(
            site_name=["indeed", "linkedin", "zip_recruiter", "naukri", "glassdoor"],
            search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            hours_old=hours_old,
            job_type=job_type,
            is_remote=is_remote,
            distance=distance,
            proxies=proxies if proxies else [],
            country_indeed='usa'
        )

        if df.empty:
            latest_search_df = pd.DataFrame()
            return "No jobs found with those filters."

        # Optional Salary Filtering (Local)
        if min_salary:
            # JobSpy returns min_amount/max_amount. We check if max is above your min.
            df = df[df['max_amount'].fillna(0) >= min_salary]

        # Save to global for the summary resource
        latest_search_df = df.copy()

        # Select columns to return to the AI
        cols = ['title', 'company', 'location', 'date_posted', 'job_url', 'min_amount', 'max_amount']
        result_list = df[cols].to_dict(orient='records')

        return json.dumps(result_list, indent=2, default=date_serializer)

    except Exception as e:
        return f"An error occurred: {str(e)}"


@mcp.resource("jobs://latest-summary")
def get_job_summary() -> str:
    """Provides a formatted Markdown table of the most recent job search."""
    if latest_search_df.empty:
        return "No results to display. Run a search first."

    cols = ['title', 'company', 'location', 'date_posted', 'max_amount']
    summary_df = latest_search_df[cols].copy()
    return "### Latest Job Search Results\n\n" + summary_df.to_markdown(index=False)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", port=8002, path = '/')
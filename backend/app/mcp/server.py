"""
CareerPilot AI MCP Server.
Exposes standard MCP tools over FastMCP / stdio or SSE transport.
Compatible with the official Python MCP SDK.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Check mcp package
try:
    from mcp.server.fastmcp import FastMCP
    mcp_app = FastMCP("careerpilot-ai")
    HAS_MCP = True
except Exception as e:
    logger.warning("FastMCP not directly importable: %s", str(e))
    mcp_app = None
    HAS_MCP = False

from app.mcp.tools import (
    tool_parse_resume,
    tool_validate_resume,
    tool_analyze_resume_against_job,
    tool_search_web,
    tool_search_greenhouse_jobs,
    tool_search_lever_jobs,
    tool_search_career_events,
    tool_verify_public_listing,
    tool_calculate_job_match,
    tool_retrieve_resume_evidence,
    tool_generate_career_roadmap,
    tool_save_career_preference,
    tool_update_learning_progress,
)

if HAS_MCP and mcp_app:
    @mcp_app.tool()
    async def parse_resume(file_path: str, file_type: str = ".txt") -> Dict[str, Any]:
        """Parse resume document (PDF, DOCX, TXT) and extract raw text and metadata."""
        return await tool_parse_resume(file_path, file_type)

    @mcp_app.tool()
    async def validate_resume(resume_text: str) -> Dict[str, Any]:
        """Perform deterministic ATS-style validation on resume text."""
        return await tool_validate_resume(resume_text)

    @mcp_app.tool()
    async def analyze_resume_against_job(
        resume_text: str,
        job_description: str,
        required_skills: List[str],
        preferred_skills: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Analyze resume text directly against job requirements and description."""
        return await tool_analyze_resume_against_job(
            resume_text, job_description, required_skills, preferred_skills
        )

    @mcp_app.tool()
    async def search_web(query: str, count: int = 5) -> Dict[str, Any]:
        """Search the web for career opportunities and events."""
        return await tool_search_web(query, count)

    @mcp_app.tool()
    async def search_greenhouse_jobs(board_token: str, query: str = "") -> List[Dict[str, Any]]:
        """Query Greenhouse Job Board API for an employer board."""
        return await tool_search_greenhouse_jobs(board_token, query)

    @mcp_app.tool()
    async def search_lever_jobs(company_slug: str, query: str = "") -> List[Dict[str, Any]]:
        """Query Lever Postings API for an employer board."""
        return await tool_search_lever_jobs(company_slug, query)

    @mcp_app.tool()
    async def search_career_events(query: str, location: Optional[str] = None) -> Dict[str, Any]:
        """Find public career fairs, hiring drives, and recruitment conferences."""
        return await tool_search_career_events(query, location)

    @mcp_app.tool()
    async def verify_public_listing(url: str) -> Dict[str, Any]:
        """Check whether a discovered public job URL is live and responsive."""
        return await tool_verify_public_listing(url)

    @mcp_app.tool()
    async def calculate_job_match(
        candidate_skills: List[str],
        candidate_experience_years: float,
        job_required_skills: List[str],
        job_preferred_skills: Optional[List[str]] = None,
        job_title: str = "",
        candidate_target_title: str = "",
        job_location: str = "",
        candidate_preferred_locations: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Compute transparent explainable match score between candidate and job."""
        return await tool_calculate_job_match(
            candidate_skills=candidate_skills,
            candidate_experience_years=candidate_experience_years,
            job_required_skills=job_required_skills,
            job_preferred_skills=job_preferred_skills,
            job_title=job_title,
            candidate_target_title=candidate_target_title,
            job_location=job_location,
            candidate_preferred_locations=candidate_preferred_locations,
        )

    @mcp_app.tool()
    async def retrieve_resume_evidence(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve indexed evidence from vector store matching a skill or qualification claim."""
        return await tool_retrieve_resume_evidence(query, top_k)

    @mcp_app.tool()
    async def generate_career_roadmap(
        target_role: str,
        current_skills: List[str],
    ) -> Dict[str, Any]:
        """Generate structured learning milestones, timelines, and curated resources."""
        return await tool_generate_career_roadmap(target_role, current_skills)

    @mcp_app.tool()
    async def save_career_preference(
        target_roles: List[str],
        preferred_locations: List[str],
        work_mode: str = "hybrid",
        employment_type: str = "full-time",
    ) -> Dict[str, Any]:
        """Save user preferences in long-term memory."""
        return await tool_save_career_preference(
            target_roles, preferred_locations, work_mode, employment_type
        )

    @mcp_app.tool()
    async def update_learning_progress(
        milestone_id: str,
        status: str,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Record progress on a learning milestone in long-term memory."""
        return await tool_update_learning_progress(milestone_id, status, notes)


def run_mcp_server():
    """Entry point to launch the MCP server over stdio."""
    if HAS_MCP and mcp_app:
        mcp_app.run(transport="stdio")
    else:
        print("MCP SDK not installed or unavailable.")


if __name__ == "__main__":
    run_mcp_server()


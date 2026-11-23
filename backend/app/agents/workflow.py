"""
CareerPilot AI - Multi-Agent System using LangGraph
Implements 6 specialized agents + supervisor for career intelligence.
"""
from typing import TypedDict, Annotated, Literal, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
import logging
import time
import json
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================
# Agent State Types
# ============================================================

class AgentState(TypedDict):
    """Shared state across all agents in the workflow."""
    # Core identifiers
    workflow_id: int
    candidate_id: int
    
    # Messages between agents
    messages: Annotated[list, add_messages]
    
    # Resume data
    resume_id: Optional[int]
    resume_text: Optional[str]
    extracted_profile: Optional[dict]
    ats_report: Optional[dict]
    resume_evidence: Optional[list]
    llm_review: Optional[dict]
    
    # Job data
    job_query: Optional[str]
    job_location: Optional[str]
    discovered_jobs: Optional[list]
    selected_jobs: Optional[list]
    job_matches: Optional[list]
    
    # Event data
    event_query: Optional[str]
    discovered_events: Optional[list]
    
    # Career planning
    target_role: Optional[str]
    skill_gaps: Optional[list]
    career_roadmap: Optional[dict]
    
    # Interview
    interview_session: Optional[dict]
    
    # Workflow control
    current_agent: Optional[str]
    next_agent: Optional[str]
    workflow_status: str
    errors: list
    warnings: list
    
    # Execution tracking
    agent_executions: list
    tool_executions: list
    start_time: Optional[float]
    
    # Failure recovery
    failed_sources: list
    retry_count: int
    fallback_used: bool
    
    # Human approval
    pending_approvals: list
    
    # Provider info
    provider_used: Optional[str]
    provider_is_proprietary: Optional[bool]


class AgentResult(BaseModel):
    """Result from an individual agent execution."""
    agent_name: str
    status: str  # success, partial, failed
    output: dict = Field(default_factory=dict)
    errors: list = Field(default_factory=list)
    warnings: list = Field(default_factory=list)
    tool_calls: list = Field(default_factory=list)
    execution_time_ms: float = 0
    provider_used: Optional[str] = None


# ============================================================
# Agent Implementations
# ============================================================

class BaseAgent:
    """Base class for all CareerPilot agents."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")
    
    def _record_execution(self, state: AgentState, result: AgentResult) -> AgentState:
        """Record this agent's execution in the state."""
        execution_record = {
            "agent_name": self.name,
            "status": result.status,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "execution_time_ms": result.execution_time_ms,
            "tool_calls": result.tool_calls,
            "errors": result.errors,
            "warnings": result.warnings,
            "provider_used": result.provider_used,
        }
        state["agent_executions"] = state.get("agent_executions", []) + [execution_record]
        
        if result.errors:
            state["errors"] = state.get("errors", []) + result.errors
        if result.warnings:
            state["warnings"] = state.get("warnings", []) + result.warnings
        
        return state


class ResumeIntelligenceAgent(BaseAgent):
    """Agent 1: Analyzes resumes, extracts structured information, runs ATS checks."""
    
    def __init__(self):
        super().__init__("resume_intelligence")
    
    async def run(self, state: AgentState) -> AgentState:
        start = time.time()
        self.logger.info("Resume Intelligence Agent starting...")
        
        tool_calls = []
        errors = []
        warnings = []
        
        try:
            from app.services.resume.parser import ResumeParser
            from app.services.resume.extractor import ResumeExtractor
            from app.services.resume.ats_checker import ATSChecker
            from app.services.resume.analyzer import ResumeAnalyzer
            
            # Step 1: Parse resume if we have a resume_id but no text
            if state.get("resume_id") and not state.get("resume_text"):
                self.logger.info(f"Parsing resume {state['resume_id']}")
                # In a real workflow, we'd load the file from the database
                tool_calls.append({
                    "tool": "parse_resume",
                    "input": {"resume_id": state["resume_id"]},
                    "status": "skipped_no_file",
                })
            
            resume_text = state.get("resume_text", "")
            
            if not resume_text:
                errors.append("No resume text available for analysis")
                result = AgentResult(
                    agent_name=self.name,
                    status="failed",
                    errors=errors,
                    execution_time_ms=(time.time() - start) * 1000
                )
                state = self._record_execution(state, result)
                state["workflow_status"] = "partial"
                return state
            
            # Step 2: Extract structured profile
            extractor = ResumeExtractor()
            profile = extractor.extract(resume_text)
            state["extracted_profile"] = profile
            tool_calls.append({
                "tool": "extract_profile",
                "input": {"text_length": len(resume_text)},
                "status": "success",
                "output_summary": f"Extracted profile for {profile.get('name', 'Unknown')}"
            })
            
            # Step 3: Run ATS checks
            job_desc = None
            if state.get("selected_jobs") and len(state["selected_jobs"]) > 0:
                job_desc = state["selected_jobs"][0].get("description", "")
            
            checker = ATSChecker()
            ats_report = checker.check(resume_text, profile, job_desc)
            state["ats_report"] = ats_report
            tool_calls.append({
                "tool": "validate_resume",
                "input": {"has_job_desc": job_desc is not None},
                "status": "success",
                "output_summary": f"ATS Score: {ats_report.get('overall_score', 0)}/100"
            })
            
            # Step 4: Try LLM-enhanced review
            try:
                from app.llm.manager import llm_manager
                if llm_manager.is_available():
                    analyzer = ResumeAnalyzer()
                    llm_review = await analyzer._run_llm_review(resume_text, profile, job_desc)
                    state["llm_review"] = llm_review
                    state["provider_used"] = llm_review.get("provider_used")
                    state["provider_is_proprietary"] = llm_review.get("is_proprietary", False)
                    tool_calls.append({
                        "tool": "llm_review",
                        "input": {"provider": llm_review.get("provider_used")},
                        "status": "success",
                    })
                else:
                    warnings.append("LLM unavailable - skipping enhanced review")
            except Exception as e:
                warnings.append(f"LLM review failed: {str(e)} - deterministic checks still available")
            
            result = AgentResult(
                agent_name=self.name,
                status="success",
                output={"ats_score": ats_report.get("overall_score", 0)},
                tool_calls=tool_calls,
                warnings=warnings,
                execution_time_ms=(time.time() - start) * 1000,
                provider_used=state.get("provider_used"),
            )
            
        except Exception as e:
            self.logger.error(f"Resume Intelligence Agent failed: {e}")
            errors.append(f"Resume analysis failed: {str(e)}")
            result = AgentResult(
                agent_name=self.name,
                status="failed",
                errors=errors,
                tool_calls=tool_calls,
                execution_time_ms=(time.time() - start) * 1000
            )
            state["workflow_status"] = "partial"
        
        state = self._record_execution(state, result)
        return state


class JobDiscoveryAgent(BaseAgent):
    """Agent 2: Discovers job opportunities from multiple sources."""
    
    def __init__(self):
        super().__init__("job_discovery")
    
    async def run(self, state: AgentState) -> AgentState:
        start = time.time()
        self.logger.info("Job Discovery Agent starting...")
        
        tool_calls = []
        errors = []
        warnings = []
        failed_sources = []
        
        try:
            from app.services.jobs.discovery import JobDiscoveryService
            
            query = state.get("job_query", "")
            location = state.get("job_location", "")
            
            if not query:
                # Derive query from extracted profile
                profile = state.get("extracted_profile", {})
                if profile:
                    skills = profile.get("skills", {})
                    tech_skills = skills.get("technical", []) if isinstance(skills, dict) else []
                    target = state.get("target_role", "")
                    query = f"{target} {' '.join(tech_skills[:5])}" if target else "software developer"
                else:
                    query = "software developer entry level"
            
            discovery = JobDiscoveryService()
            result_obj = await discovery.discover(
                query=query,
                location=location,
                sources=None,
            )
            
            raw_dict = result_obj.model_dump() if hasattr(result_obj, "model_dump") else (result_obj if isinstance(result_obj, dict) else {})
            state["discovered_jobs"] = raw_dict.get("jobs", [])
            sources_searched = raw_dict.get("sources_searched", raw_dict.get("sources_used", []))
            failed_sources = [e.split(":")[0].strip() for e in raw_dict.get("errors", [])]
            state["failed_sources"] = state.get("failed_sources", []) + failed_sources
            
            for source in sources_searched:
                tool_calls.append({
                    "tool": f"search_{source}",
                    "input": {"query": query, "location": location},
                    "status": "success",
                    "output_summary": f"Found jobs from {source}"
                })
            
            for source in failed_sources:
                tool_calls.append({
                    "tool": f"search_{source}",
                    "input": {"query": query},
                    "status": "failed",
                })
                warnings.append(f"Source '{source}' failed - results may be incomplete")
            
            if not state["discovered_jobs"]:
                warnings.append("No jobs discovered from any source")
            
            result = AgentResult(
                agent_name=self.name,
                status="success" if state["discovered_jobs"] else "partial",
                output={"jobs_found": len(state["discovered_jobs"])},
                tool_calls=tool_calls,
                warnings=warnings,
                execution_time_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            self.logger.error(f"Job Discovery Agent failed: {e}")
            errors.append(f"Job discovery failed: {str(e)}")
            state["discovered_jobs"] = []
            result = AgentResult(
                agent_name=self.name,
                status="failed",
                errors=errors,
                tool_calls=tool_calls,
                execution_time_ms=(time.time() - start) * 1000
            )
        
        state = self._record_execution(state, result)
        return state


class JobMatchingAgent(BaseAgent):
    """Agent 3: Matches candidate skills to job requirements with transparent scoring."""
    
    def __init__(self):
        super().__init__("job_matching")
    
    async def run(self, state: AgentState) -> AgentState:
        start = time.time()
        self.logger.info("Job Matching Agent starting...")
        
        tool_calls = []
        errors = []
        warnings = []
        
        try:
            from app.services.matching.matcher import JobMatcher
            
            profile = state.get("extracted_profile", {})
            jobs = state.get("discovered_jobs", [])
            
            if not profile:
                errors.append("No candidate profile available for matching")
                result = AgentResult(
                    agent_name=self.name, status="failed",
                    errors=errors, execution_time_ms=(time.time() - start) * 1000
                )
                state = self._record_execution(state, result)
                return state
            
            if not jobs:
                warnings.append("No jobs available for matching")
                state["job_matches"] = []
                result = AgentResult(
                    agent_name=self.name, status="partial",
                    warnings=warnings, execution_time_ms=(time.time() - start) * 1000
                )
                state = self._record_execution(state, result)
                return state
            
            matcher = JobMatcher()
            matches = []
            skill_gaps = set()
            
            for job in jobs:
                try:
                    match_res = matcher.match(profile, job)
                    match = match_res.model_dump() if hasattr(match_res, "model_dump") else match_res
                    match["job_title"] = job.get("title", "Unknown")
                    match["employer"] = job.get("company", job.get("employer", "Unknown"))
                    matches.append(match)
                    tool_calls.append({
                        "tool": "calculate_job_match",
                        "input": {"job_title": job.get("title", "Unknown")},
                        "status": "success",
                        "output_summary": f"Match score: {match.get('overall_score', 0):.0f}%"
                    })
                    # Collect skill gaps
                    for gap in match.get("skill_gaps", []):
                        gap_name = gap.get("skill") if isinstance(gap, dict) else str(gap)
                        skill_gaps.add(gap_name)
                except Exception as e:
                    warnings.append(f"Failed to match job '{job.get('title', 'Unknown')}': {str(e)}")
            
            # Sort by score
            matches.sort(key=lambda m: m.get("overall_score", 0), reverse=True)
            state["job_matches"] = matches
            state["skill_gaps"] = list(skill_gaps)
            
            # Try LLM explanation for top matches
            try:
                from app.llm.manager import llm_manager
                if llm_manager.is_available() and matches:
                    top_match = matches[0]
                    prompt = f"""Briefly explain why this candidate is a {'good' if top_match['overall_score'] > 70 else 'partial'} match for the role of {top_match.get('job_title', 'the position')}.
Score: {top_match['overall_score']:.0f}%
Matching skills: {', '.join(list(top_match.get('skill_matches', {}).keys())[:10])}
Missing skills: {', '.join(top_match.get('skill_gaps', [])[:5])}
Keep it concise and evidence-based."""
                    
                    response = await llm_manager.generate(prompt)
                    top_match["llm_explanation"] = response.content
                    state["provider_used"] = response.provider
                    state["provider_is_proprietary"] = "gemini" in response.provider.lower()
            except Exception:
                pass  # LLM explanation is optional
            
            result = AgentResult(
                agent_name=self.name,
                status="success",
                output={"matches_computed": len(matches), "top_score": matches[0]["overall_score"] if matches else 0},
                tool_calls=tool_calls,
                warnings=warnings,
                execution_time_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            self.logger.error(f"Job Matching Agent failed: {e}")
            errors.append(f"Job matching failed: {str(e)}")
            state["job_matches"] = []
            result = AgentResult(
                agent_name=self.name, status="failed",
                errors=errors, execution_time_ms=(time.time() - start) * 1000
            )
        
        state = self._record_execution(state, result)
        return state


class CareerPlanningAgent(BaseAgent):
    """Agent 4: Generates personalized career roadmaps based on skill gaps."""
    
    def __init__(self):
        super().__init__("career_planning")
    
    async def run(self, state: AgentState) -> AgentState:
        start = time.time()
        self.logger.info("Career Planning Agent starting...")
        
        tool_calls = []
        errors = []
        warnings = []
        
        try:
            from app.services.career.roadmap import CareerRoadmapService
            
            profile = state.get("extracted_profile", {})
            skill_gaps = state.get("skill_gaps", [])
            target_role = state.get("target_role", "")
            
            if not target_role and state.get("job_matches"):
                # Infer target role from top match
                target_role = state["job_matches"][0].get("job_title", "Software Developer")
            
            if not target_role:
                target_role = "Software Developer"
                warnings.append("No target role specified, using default")
            
            roadmap_service = CareerRoadmapService()
            
            current_skills = []
            if profile:
                skills = profile.get("skills", {})
                if isinstance(skills, dict):
                    current_skills = skills.get("technical", []) + skills.get("soft", [])
                elif isinstance(skills, list):
                    current_skills = skills
            
            roadmap = roadmap_service.generate_roadmap(
                current_skills=current_skills,
                target_role=target_role,
                skill_gaps=skill_gaps,
            )
            
            state["career_roadmap"] = roadmap
            tool_calls.append({
                "tool": "generate_career_roadmap",
                "input": {"target_role": target_role, "gaps_count": len(skill_gaps)},
                "status": "success",
                "output_summary": f"Generated roadmap with {len(roadmap.get('milestones', []))} milestones"
            })
            
            # Try LLM enhancement
            try:
                from app.llm.manager import llm_manager
                if llm_manager.is_available():
                    prompt = f"""Given a candidate with skills: {', '.join(current_skills[:10])}
Target role: {target_role}
Skill gaps: {', '.join(skill_gaps[:10])}

Suggest 3 specific, actionable learning resources or projects for the top skill gaps.
Be specific with resource names and keep suggestions practical for a student."""
                    
                    response = await llm_manager.generate(prompt)
                    roadmap["llm_suggestions"] = response.content
                    roadmap["provider_used"] = response.provider
            except Exception:
                warnings.append("LLM suggestions unavailable - using deterministic roadmap")
            
            result = AgentResult(
                agent_name=self.name,
                status="success",
                output={"milestones": len(roadmap.get("milestones", []))},
                tool_calls=tool_calls,
                warnings=warnings,
                execution_time_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            self.logger.error(f"Career Planning Agent failed: {e}")
            errors.append(f"Career planning failed: {str(e)}")
            result = AgentResult(
                agent_name=self.name, status="failed",
                errors=errors, execution_time_ms=(time.time() - start) * 1000
            )
        
        state = self._record_execution(state, result)
        return state


class InterviewPrepAgent(BaseAgent):
    """Agent 5: Generates interview questions and evaluates responses."""
    
    def __init__(self):
        super().__init__("interview_prep")
    
    async def run(self, state: AgentState) -> AgentState:
        start = time.time()
        self.logger.info("Interview Prep Agent starting...")
        
        tool_calls = []
        errors = []
        warnings = []
        
        try:
            from app.services.interview.engine import InterviewEngine
            
            profile = state.get("extracted_profile", {})
            target_role = state.get("target_role", "Software Developer")
            
            skills = []
            if profile:
                skill_data = profile.get("skills", {})
                if isinstance(skill_data, dict):
                    skills = skill_data.get("technical", [])
                elif isinstance(skill_data, list):
                    skills = skill_data
            
            engine = InterviewEngine()
            session = engine.generate_session(
                role=target_role,
                skills=skills,
                session_type="technical"
            )
            
            state["interview_session"] = session
            tool_calls.append({
                "tool": "generate_interview",
                "input": {"role": target_role, "type": "technical"},
                "status": "success",
                "output_summary": f"Generated {len(session.get('questions', []))} questions"
            })
            
            result = AgentResult(
                agent_name=self.name,
                status="success",
                output={"questions_generated": len(session.get("questions", []))},
                tool_calls=tool_calls,
                warnings=warnings,
                execution_time_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            self.logger.error(f"Interview Prep Agent failed: {e}")
            errors.append(f"Interview prep failed: {str(e)}")
            result = AgentResult(
                agent_name=self.name, status="failed",
                errors=errors, execution_time_ms=(time.time() - start) * 1000
            )
        
        state = self._record_execution(state, result)
        return state


class CareerEventsAgent(BaseAgent):
    """Agent 6: Discovers career fairs and recruitment events."""
    
    def __init__(self):
        super().__init__("career_events")
    
    async def run(self, state: AgentState) -> AgentState:
        start = time.time()
        self.logger.info("Career Events Agent starting...")
        
        tool_calls = []
        errors = []
        warnings = []
        
        try:
            from app.services.events.discovery import EventDiscoveryService
            
            query = state.get("event_query", "")
            location = state.get("job_location", "")
            target_role = state.get("target_role", "")
            
            if not query:
                query = f"{target_role} career fair recruitment event" if target_role else "career fair recruitment event"
            
            service = EventDiscoveryService()
            result_obj = await service.discover(
                query=query,
                location=location,
            )
            raw_event_dict = result_obj.model_dump() if hasattr(result_obj, "model_dump") else (result_obj if isinstance(result_obj, dict) else {})
            state["discovered_events"] = raw_event_dict.get("events", [])
            
            tool_calls.append({
                "tool": "search_career_events",
                "input": {"query": query, "location": location},
                "status": "success" if state["discovered_events"] else "partial",
                "output_summary": f"Found {len(state['discovered_events'])} events"
            })
            
            if not state["discovered_events"]:
                warnings.append("No career events found - search may need different terms or configured sources")
            
            result = AgentResult(
                agent_name=self.name,
                status="success" if state["discovered_events"] else "partial",
                output={"events_found": len(state["discovered_events"])},
                tool_calls=tool_calls,
                warnings=warnings,
                execution_time_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            self.logger.error(f"Career Events Agent failed: {e}")
            errors.append(f"Event discovery failed: {str(e)}")
            state["discovered_events"] = []
            result = AgentResult(
                agent_name=self.name, status="failed",
                errors=errors, execution_time_ms=(time.time() - start) * 1000
            )
        
        state = self._record_execution(state, result)
        return state


# ============================================================
# Supervisor Agent
# ============================================================

class SupervisorAgent(BaseAgent):
    """Supervisor: Coordinates all agents, manages workflow, handles failures."""
    
    def __init__(self):
        super().__init__("supervisor")
        self.agents = {
            "resume_intelligence": ResumeIntelligenceAgent(),
            "job_discovery": JobDiscoveryAgent(),
            "job_matching": JobMatchingAgent(),
            "career_planning": CareerPlanningAgent(),
            "interview_prep": InterviewPrepAgent(),
            "career_events": CareerEventsAgent(),
        }
    
    def plan_workflow(self, state: AgentState) -> list[str]:
        """Determine which agents to run and in what order."""
        plan = []
        
        # Always start with resume if available
        if state.get("resume_text") or state.get("resume_id"):
            plan.append("resume_intelligence")
        
        # Job discovery can run in parallel with resume analysis
        if state.get("job_query") or state.get("target_role") or state.get("extracted_profile"):
            plan.append("job_discovery")
        
        # Career events can also run in parallel
        plan.append("career_events")
        
        # Matching requires both resume and jobs
        if "resume_intelligence" in plan and "job_discovery" in plan:
            plan.append("job_matching")
        
        # Career planning requires profile and ideally matches
        if "resume_intelligence" in plan:
            plan.append("career_planning")
        
        # Interview prep can run with just a target role
        if state.get("target_role") or "resume_intelligence" in plan:
            plan.append("interview_prep")
        
        return plan
    
    def validate_outputs(self, state: AgentState) -> list[str]:
        """Validate agent outputs and identify issues."""
        issues = []
        
        # Check for evidence disagreements
        if state.get("ats_report") and state.get("llm_review"):
            ats_checks = state["ats_report"].get("checks", [])
            llm_suggestions = state.get("llm_review", {}).get("suggestions", [])
            # Flag if LLM claims skill missing but ATS found it
            for check in ats_checks:
                if check.get("check_name") == "keyword_coverage" and check.get("passed"):
                    for suggestion in llm_suggestions:
                        if "missing" in suggestion.lower():
                            issues.append(
                                f"Potential disagreement: ATS found good keyword coverage "
                                f"but LLM flagged missing items. Evidence retrieval recommended."
                            )
                            break
        
        # Check job verification
        if state.get("discovered_jobs"):
            unverified = [j for j in state["discovered_jobs"] 
                         if j.get("verification_status") in ("unverified", "unavailable")]
            if unverified:
                issues.append(
                    f"{len(unverified)} job(s) have unverified status. "
                    f"Recommend re-checking before applying."
                )
        
        # Check event dates
        if state.get("discovered_events"):
            for event in state["discovered_events"]:
                if event.get("verification_status") == "unverified":
                    issues.append(
                        f"Event '{event.get('name', 'Unknown')}' has unverified details."
                    )
        
        return issues
    
    def resolve_conflicts(self, state: AgentState) -> AgentState:
        """Attempt to resolve conflicts between agent outputs."""
        # If resume evidence contradicts LLM claim, prefer evidence
        if state.get("resume_evidence") and state.get("llm_review"):
            review = state["llm_review"]
            suggestions = review.get("suggestions", [])
            resolved_suggestions = []
            
            for suggestion in suggestions:
                # Check if resume evidence contradicts this suggestion
                contradicted = False
                for evidence in state.get("resume_evidence", []):
                    if evidence.get("is_verified") and evidence.get("confidence", 0) > 0.8:
                        # If evidence directly addresses the suggestion topic
                        claim = evidence.get("claim", "").lower()
                        if any(word in suggestion.lower() for word in claim.split() if len(word) > 3):
                            contradicted = True
                            resolved_suggestions.append(
                                f"[RESOLVED] {suggestion} — Evidence found: {evidence['evidence_text'][:100]}"
                            )
                            break
                
                if not contradicted:
                    resolved_suggestions.append(suggestion)
            
            review["suggestions"] = resolved_suggestions
            state["llm_review"] = review
        
        return state
    
    def produce_final_report(self, state: AgentState) -> dict:
        """Compile the final comprehensive report."""
        report = {
            "workflow_id": state.get("workflow_id"),
            "status": state.get("workflow_status", "completed"),
            "candidate_id": state.get("candidate_id"),
            "timestamp": datetime.utcnow().isoformat(),
            
            # Resume analysis
            "resume_analysis": {
                "ats_score": state.get("ats_report", {}).get("overall_score"),
                "ats_report": state.get("ats_report"),
                "extracted_profile": state.get("extracted_profile"),
                "llm_review": state.get("llm_review"),
                "evidence": state.get("resume_evidence"),
            },
            
            # Job discovery
            "job_discovery": {
                "total_found": len(state.get("discovered_jobs", [])),
                "jobs": state.get("discovered_jobs", []),
                "failed_sources": state.get("failed_sources", []),
            },
            
            # Job matching
            "job_matching": {
                "matches": state.get("job_matches", []),
                "skill_gaps": state.get("skill_gaps", []),
            },
            
            # Career planning
            "career_roadmap": state.get("career_roadmap"),
            
            # Interview
            "interview_session": state.get("interview_session"),
            
            # Events
            "career_events": {
                "events": state.get("discovered_events", []),
            },
            
            # Execution metadata
            "execution": {
                "agent_executions": state.get("agent_executions", []),
                "tool_executions": state.get("tool_executions", []),
                "errors": state.get("errors", []),
                "warnings": state.get("warnings", []),
                "provider_used": state.get("provider_used"),
                "provider_is_proprietary": state.get("provider_is_proprietary"),
                "fallback_used": state.get("fallback_used", False),
            },
        }
        
        return report


# ============================================================
# LangGraph Workflow Builder
# ============================================================

def create_workflow() -> StateGraph:
    """Create the LangGraph workflow for CareerPilot AI."""
    
    supervisor = SupervisorAgent()
    
    # Node functions
    async def supervisor_plan(state: AgentState) -> AgentState:
        """Supervisor plans which agents to run."""
        state["workflow_status"] = "planning"
        state["start_time"] = time.time()
        state["agent_executions"] = []
        state["tool_executions"] = []
        state["errors"] = []
        state["warnings"] = []
        state["failed_sources"] = []
        state["fallback_used"] = False
        state["pending_approvals"] = []
        state["retry_count"] = 0
        
        plan = supervisor.plan_workflow(state)
        state["messages"] = [{"role": "system", "content": f"Workflow plan: {', '.join(plan)}"}]
        state["workflow_status"] = "running"
        return state
    
    async def run_resume_agent(state: AgentState) -> AgentState:
        """Run the Resume Intelligence Agent."""
        state["current_agent"] = "resume_intelligence"
        return await supervisor.agents["resume_intelligence"].run(state)
    
    async def run_job_discovery(state: AgentState) -> AgentState:
        """Run the Job Discovery Agent."""
        state["current_agent"] = "job_discovery"
        return await supervisor.agents["job_discovery"].run(state)
    
    async def run_events_agent(state: AgentState) -> AgentState:
        """Run the Career Events Agent."""
        state["current_agent"] = "career_events"
        return await supervisor.agents["career_events"].run(state)
    
    async def run_matching_agent(state: AgentState) -> AgentState:
        """Run the Job Matching Agent."""
        state["current_agent"] = "job_matching"
        return await supervisor.agents["job_matching"].run(state)
    
    async def run_career_agent(state: AgentState) -> AgentState:
        """Run the Career Planning Agent."""
        state["current_agent"] = "career_planning"
        return await supervisor.agents["career_planning"].run(state)
    
    async def run_interview_agent(state: AgentState) -> AgentState:
        """Run the Interview Prep Agent."""
        state["current_agent"] = "interview_prep"
        return await supervisor.agents["interview_prep"].run(state)
    
    async def supervisor_validate(state: AgentState) -> AgentState:
        """Supervisor validates outputs and resolves conflicts."""
        state["current_agent"] = "supervisor"
        
        issues = supervisor.validate_outputs(state)
        if issues:
            state["warnings"] = state.get("warnings", []) + issues
        
        state = supervisor.resolve_conflicts(state)
        
        # Produce final report
        report = supervisor.produce_final_report(state)
        state["messages"] = state.get("messages", []) + [
            {"role": "system", "content": f"Final report compiled. Status: {state['workflow_status']}"}
        ]
        
        return state
    
    async def supervisor_finalize(state: AgentState) -> AgentState:
        """Finalize the workflow."""
        if not any(e.get("status") == "failed" for e in state.get("agent_executions", [])):
            state["workflow_status"] = "completed"
        elif any(e.get("status") == "success" for e in state.get("agent_executions", [])):
            state["workflow_status"] = "partial"
        else:
            state["workflow_status"] = "failed"
        
        return state
    
    # Routing function
    def should_continue(state: AgentState) -> str:
        """Determine next step based on current state."""
        if state.get("errors") and len(state.get("errors", [])) > 10:
            return "validate"  # Too many errors, skip to validation
        return "continue"
    
    # Build the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("plan", supervisor_plan)
    workflow.add_node("resume_agent", run_resume_agent)
    workflow.add_node("job_discovery", run_job_discovery)
    workflow.add_node("events_agent", run_events_agent)
    workflow.add_node("matching_agent", run_matching_agent)
    workflow.add_node("career_agent", run_career_agent)
    workflow.add_node("interview_agent", run_interview_agent)
    workflow.add_node("validate", supervisor_validate)
    workflow.add_node("finalize", supervisor_finalize)
    
    # Add edges - sequential flow with proper dependencies
    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "resume_agent")
    workflow.add_edge("resume_agent", "job_discovery")
    workflow.add_edge("job_discovery", "events_agent")
    workflow.add_edge("events_agent", "matching_agent")
    workflow.add_edge("matching_agent", "career_agent")
    workflow.add_edge("career_agent", "interview_agent")
    workflow.add_edge("interview_agent", "validate")
    workflow.add_edge("validate", "finalize")
    workflow.add_edge("finalize", END)
    
    return workflow


def compile_workflow():
    """Compile and return the workflow graph."""
    workflow = create_workflow()
    return workflow.compile()


# Singleton compiled workflow
_compiled_workflow = None

def get_workflow():
    """Get or create the compiled workflow."""
    global _compiled_workflow
    if _compiled_workflow is None:
        _compiled_workflow = compile_workflow()
    return _compiled_workflow


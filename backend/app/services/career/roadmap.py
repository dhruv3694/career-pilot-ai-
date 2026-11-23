"""
Career roadmap generator.

Produces a structured learning roadmap for a candidate to transition into a
target role. Works fully deterministically with built-in skill and resource
maps; optionally enhances output with an LLM when available.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class SkillGap(BaseModel):
    """A single skill gap between current and target level."""

    skill: str
    current_level: str = Field(
        ...,
        description="none, beginner, intermediate, or advanced",
        pattern=r"^(none|beginner|intermediate|advanced)$",
    )
    target_level: str = Field(
        ...,
        description="beginner, intermediate, or advanced",
        pattern=r"^(beginner|intermediate|advanced)$",
    )
    priority: str = Field(
        ...,
        description="high, medium, or low",
        pattern=r"^(high|medium|low)$",
    )


class Resource(BaseModel):
    """A learning resource recommendation."""

    name: str
    url: str
    resource_type: str = Field(
        ...,
        description="course, book, tutorial, project, or certification",
    )
    provider: str = ""
    is_free: bool = True


class Milestone(BaseModel):
    """A single milestone on the learning roadmap."""

    title: str
    description: str
    skills_to_learn: list[str] = Field(default_factory=list)
    resources: list[Resource] = Field(default_factory=list)
    estimated_weeks: int = 1
    order: int = 0


class RoadmapResult(BaseModel):
    """Complete career roadmap output."""

    candidate_id: int
    target_role: str
    current_skills: list[str] = Field(default_factory=list)
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    milestones: list[Milestone] = Field(default_factory=list)
    estimated_total_weeks: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


# ---------------------------------------------------------------------------
# Built-in knowledge bases
# ---------------------------------------------------------------------------

ROLE_SKILL_MAP: dict[str, dict[str, str]] = {
    "software_engineer": {
        "Python": "intermediate",
        "JavaScript": "intermediate",
        "SQL": "intermediate",
        "Git": "intermediate",
        "Data Structures": "intermediate",
        "Algorithms": "intermediate",
        "REST APIs": "intermediate",
        "Testing": "intermediate",
    },
    "data_scientist": {
        "Python": "intermediate",
        "SQL": "intermediate",
        "Statistics": "intermediate",
        "Machine Learning": "intermediate",
        "Pandas": "intermediate",
        "NumPy": "intermediate",
        "Data Visualization": "intermediate",
        "Jupyter": "beginner",
    },
    "frontend_developer": {
        "JavaScript": "advanced",
        "TypeScript": "intermediate",
        "React": "intermediate",
        "CSS": "intermediate",
        "HTML": "intermediate",
        "Git": "intermediate",
        "Testing": "intermediate",
        "Responsive Design": "intermediate",
    },
    "backend_developer": {
        "Python": "intermediate",
        "SQL": "intermediate",
        "REST APIs": "intermediate",
        "Docker": "intermediate",
        "Git": "intermediate",
        "Databases": "intermediate",
        "Testing": "intermediate",
        "Security": "beginner",
    },
    "devops_engineer": {
        "Docker": "advanced",
        "Kubernetes": "intermediate",
        "CI/CD": "intermediate",
        "AWS/Cloud": "intermediate",
        "Linux": "intermediate",
        "Terraform": "intermediate",
        "Monitoring": "intermediate",
        "Scripting": "intermediate",
    },
    "ml_engineer": {
        "Python": "advanced",
        "Machine Learning": "advanced",
        "Deep Learning": "intermediate",
        "MLOps": "intermediate",
        "Docker": "intermediate",
        "SQL": "intermediate",
        "TensorFlow/PyTorch": "intermediate",
        "Data Pipelines": "intermediate",
    },
    "product_manager": {
        "Product Strategy": "intermediate",
        "User Research": "intermediate",
        "Data Analysis": "intermediate",
        "Agile": "intermediate",
        "Roadmapping": "intermediate",
        "A/B Testing": "beginner",
        "Communication": "advanced",
    },
}

RESOURCE_MAP: dict[str, list[dict[str, Any]]] = {
    "Python": [
        {
            "name": "Python for Everybody (Coursera)",
            "url": "https://www.coursera.org/specializations/python",
            "resource_type": "course",
            "provider": "Coursera / University of Michigan",
            "is_free": True,
        },
        {
            "name": "Automate the Boring Stuff with Python",
            "url": "https://automatetheboringstuff.com/",
            "resource_type": "book",
            "provider": "Al Sweigart",
            "is_free": True,
        },
        {
            "name": "Real Python Tutorials",
            "url": "https://realpython.com/",
            "resource_type": "tutorial",
            "provider": "Real Python",
            "is_free": True,
        },
    ],
    "JavaScript": [
        {
            "name": "The Odin Project – JavaScript",
            "url": "https://www.theodinproject.com/paths/full-stack-javascript",
            "resource_type": "course",
            "provider": "The Odin Project",
            "is_free": True,
        },
        {
            "name": "Eloquent JavaScript",
            "url": "https://eloquentjavascript.net/",
            "resource_type": "book",
            "provider": "Marijn Haverbeke",
            "is_free": True,
        },
    ],
    "TypeScript": [
        {
            "name": "TypeScript Handbook",
            "url": "https://www.typescriptlang.org/docs/handbook/",
            "resource_type": "tutorial",
            "provider": "Microsoft",
            "is_free": True,
        },
        {
            "name": "Execute Program – TypeScript",
            "url": "https://www.executeprogram.com/courses/typescript",
            "resource_type": "course",
            "provider": "Execute Program",
            "is_free": False,
        },
    ],
    "SQL": [
        {
            "name": "SQLBolt – Interactive SQL Lessons",
            "url": "https://sqlbolt.com/",
            "resource_type": "tutorial",
            "provider": "SQLBolt",
            "is_free": True,
        },
        {
            "name": "Mode Analytics SQL Tutorial",
            "url": "https://mode.com/sql-tutorial/",
            "resource_type": "tutorial",
            "provider": "Mode Analytics",
            "is_free": True,
        },
    ],
    "Git": [
        {
            "name": "Pro Git Book",
            "url": "https://git-scm.com/book/en/v2",
            "resource_type": "book",
            "provider": "Git SCM",
            "is_free": True,
        },
        {
            "name": "Learn Git Branching",
            "url": "https://learngitbranching.js.org/",
            "resource_type": "tutorial",
            "provider": "Learn Git Branching",
            "is_free": True,
        },
    ],
    "React": [
        {
            "name": "React Official Tutorial",
            "url": "https://react.dev/learn",
            "resource_type": "tutorial",
            "provider": "React",
            "is_free": True,
        },
        {
            "name": "Full Stack Open – React",
            "url": "https://fullstackopen.com/en/",
            "resource_type": "course",
            "provider": "University of Helsinki",
            "is_free": True,
        },
    ],
    "Docker": [
        {
            "name": "Docker Getting Started",
            "url": "https://docs.docker.com/get-started/",
            "resource_type": "tutorial",
            "provider": "Docker",
            "is_free": True,
        },
        {
            "name": "Docker Mastery (Udemy)",
            "url": "https://www.udemy.com/course/docker-mastery/",
            "resource_type": "course",
            "provider": "Udemy / Bret Fisher",
            "is_free": False,
        },
    ],
    "Kubernetes": [
        {
            "name": "Kubernetes Basics (official)",
            "url": "https://kubernetes.io/docs/tutorials/kubernetes-basics/",
            "resource_type": "tutorial",
            "provider": "Kubernetes",
            "is_free": True,
        },
        {
            "name": "CKA Certification",
            "url": "https://training.linuxfoundation.org/certification/certified-kubernetes-administrator-cka/",
            "resource_type": "certification",
            "provider": "Linux Foundation",
            "is_free": False,
        },
    ],
    "Machine Learning": [
        {
            "name": "Machine Learning by Andrew Ng (Coursera)",
            "url": "https://www.coursera.org/learn/machine-learning",
            "resource_type": "course",
            "provider": "Coursera / Stanford",
            "is_free": True,
        },
        {
            "name": "Hands-On Machine Learning (Book)",
            "url": "https://www.oreilly.com/library/view/hands-on-machine-learning/9781098125967/",
            "resource_type": "book",
            "provider": "O'Reilly",
            "is_free": False,
        },
        {
            "name": "Kaggle Learn",
            "url": "https://www.kaggle.com/learn",
            "resource_type": "tutorial",
            "provider": "Kaggle",
            "is_free": True,
        },
    ],
    "Deep Learning": [
        {
            "name": "Deep Learning Specialization (Coursera)",
            "url": "https://www.coursera.org/specializations/deep-learning",
            "resource_type": "course",
            "provider": "Coursera / deeplearning.ai",
            "is_free": True,
        },
        {
            "name": "Fast.ai Practical Deep Learning",
            "url": "https://course.fast.ai/",
            "resource_type": "course",
            "provider": "fast.ai",
            "is_free": True,
        },
    ],
    "Statistics": [
        {
            "name": "Khan Academy – Statistics & Probability",
            "url": "https://www.khanacademy.org/math/statistics-probability",
            "resource_type": "course",
            "provider": "Khan Academy",
            "is_free": True,
        },
        {
            "name": "Think Stats (Book)",
            "url": "https://greenteapress.com/thinkstats2/",
            "resource_type": "book",
            "provider": "Green Tea Press",
            "is_free": True,
        },
    ],
    "Data Structures": [
        {
            "name": "NeetCode Roadmap",
            "url": "https://neetcode.io/roadmap",
            "resource_type": "tutorial",
            "provider": "NeetCode",
            "is_free": True,
        },
        {
            "name": "LeetCode",
            "url": "https://leetcode.com/",
            "resource_type": "project",
            "provider": "LeetCode",
            "is_free": True,
        },
    ],
    "Algorithms": [
        {
            "name": "Algorithms Specialization (Coursera)",
            "url": "https://www.coursera.org/specializations/algorithms",
            "resource_type": "course",
            "provider": "Coursera / Stanford",
            "is_free": True,
        },
        {
            "name": "Grokking Algorithms (Book)",
            "url": "https://www.manning.com/books/grokking-algorithms",
            "resource_type": "book",
            "provider": "Manning",
            "is_free": False,
        },
    ],
    "REST APIs": [
        {
            "name": "FastAPI Official Tutorial",
            "url": "https://fastapi.tiangolo.com/tutorial/",
            "resource_type": "tutorial",
            "provider": "FastAPI",
            "is_free": True,
        },
        {
            "name": "Build a REST API (project)",
            "url": "https://realpython.com/flask-connexion-rest-api/",
            "resource_type": "project",
            "provider": "Real Python",
            "is_free": True,
        },
    ],
    "Testing": [
        {
            "name": "Python Testing with pytest (Book)",
            "url": "https://pragprog.com/titles/bopytest2/python-testing-with-pytest/",
            "resource_type": "book",
            "provider": "Pragmatic Programmers",
            "is_free": False,
        },
        {
            "name": "Real Python – Testing Tutorials",
            "url": "https://realpython.com/python-testing/",
            "resource_type": "tutorial",
            "provider": "Real Python",
            "is_free": True,
        },
    ],
    "CSS": [
        {
            "name": "CSS for JavaScript Developers",
            "url": "https://css-for-js.dev/",
            "resource_type": "course",
            "provider": "Josh Comeau",
            "is_free": False,
        },
        {
            "name": "MDN CSS Guide",
            "url": "https://developer.mozilla.org/en-US/docs/Learn/CSS",
            "resource_type": "tutorial",
            "provider": "MDN",
            "is_free": True,
        },
    ],
    "HTML": [
        {
            "name": "MDN HTML Guide",
            "url": "https://developer.mozilla.org/en-US/docs/Learn/HTML",
            "resource_type": "tutorial",
            "provider": "MDN",
            "is_free": True,
        },
    ],
    "AWS/Cloud": [
        {
            "name": "AWS Cloud Practitioner Essentials",
            "url": "https://aws.amazon.com/training/digital/aws-cloud-practitioner-essentials/",
            "resource_type": "course",
            "provider": "AWS",
            "is_free": True,
        },
        {
            "name": "AWS Certified Cloud Practitioner",
            "url": "https://aws.amazon.com/certification/certified-cloud-practitioner/",
            "resource_type": "certification",
            "provider": "AWS",
            "is_free": False,
        },
    ],
    "Linux": [
        {
            "name": "Linux Journey",
            "url": "https://linuxjourney.com/",
            "resource_type": "tutorial",
            "provider": "Linux Journey",
            "is_free": True,
        },
        {
            "name": "The Linux Command Line (Book)",
            "url": "https://linuxcommand.org/tlcl.php",
            "resource_type": "book",
            "provider": "William Shotts",
            "is_free": True,
        },
    ],
    "CI/CD": [
        {
            "name": "GitHub Actions Documentation",
            "url": "https://docs.github.com/en/actions",
            "resource_type": "tutorial",
            "provider": "GitHub",
            "is_free": True,
        },
    ],
    "Terraform": [
        {
            "name": "Terraform Getting Started",
            "url": "https://developer.hashicorp.com/terraform/tutorials",
            "resource_type": "tutorial",
            "provider": "HashiCorp",
            "is_free": True,
        },
    ],
    "Pandas": [
        {
            "name": "Pandas Official Getting Started",
            "url": "https://pandas.pydata.org/docs/getting_started/index.html",
            "resource_type": "tutorial",
            "provider": "Pandas",
            "is_free": True,
        },
    ],
    "NumPy": [
        {
            "name": "NumPy Quickstart Tutorial",
            "url": "https://numpy.org/doc/stable/user/quickstart.html",
            "resource_type": "tutorial",
            "provider": "NumPy",
            "is_free": True,
        },
    ],
    "Data Visualization": [
        {
            "name": "Data Visualization with Python (Coursera)",
            "url": "https://www.coursera.org/learn/python-for-data-visualization",
            "resource_type": "course",
            "provider": "Coursera / IBM",
            "is_free": True,
        },
    ],
    "Responsive Design": [
        {
            "name": "freeCodeCamp Responsive Web Design",
            "url": "https://www.freecodecamp.org/learn/2022/responsive-web-design/",
            "resource_type": "course",
            "provider": "freeCodeCamp",
            "is_free": True,
        },
    ],
    "Security": [
        {
            "name": "OWASP Top Ten",
            "url": "https://owasp.org/www-project-top-ten/",
            "resource_type": "tutorial",
            "provider": "OWASP",
            "is_free": True,
        },
    ],
    "Databases": [
        {
            "name": "CMU Database Systems (YouTube)",
            "url": "https://www.youtube.com/playlist?list=PLSE8ODhjZXjbj8BMuIrRcacnQh20hmY9g",
            "resource_type": "course",
            "provider": "CMU",
            "is_free": True,
        },
    ],
    "Monitoring": [
        {
            "name": "Prometheus & Grafana Tutorial",
            "url": "https://prometheus.io/docs/tutorials/getting_started/",
            "resource_type": "tutorial",
            "provider": "Prometheus",
            "is_free": True,
        },
    ],
    "MLOps": [
        {
            "name": "Made With ML – MLOps",
            "url": "https://madewithml.com/",
            "resource_type": "course",
            "provider": "Made With ML",
            "is_free": True,
        },
    ],
    "TensorFlow/PyTorch": [
        {
            "name": "PyTorch Official Tutorials",
            "url": "https://pytorch.org/tutorials/",
            "resource_type": "tutorial",
            "provider": "PyTorch",
            "is_free": True,
        },
        {
            "name": "TensorFlow Developer Certificate",
            "url": "https://www.tensorflow.org/certificate",
            "resource_type": "certification",
            "provider": "Google",
            "is_free": False,
        },
    ],
    "Data Pipelines": [
        {
            "name": "Apache Airflow Tutorial",
            "url": "https://airflow.apache.org/docs/apache-airflow/stable/tutorial/index.html",
            "resource_type": "tutorial",
            "provider": "Apache",
            "is_free": True,
        },
    ],
    "Product Strategy": [
        {
            "name": "Inspired: How to Create Tech Products (Book)",
            "url": "https://www.svpg.com/inspired-how-to-create-tech-products-customers-love/",
            "resource_type": "book",
            "provider": "SVPG",
            "is_free": False,
        },
    ],
    "User Research": [
        {
            "name": "Google UX Design Certificate",
            "url": "https://www.coursera.org/professional-certificates/google-ux-design",
            "resource_type": "course",
            "provider": "Coursera / Google",
            "is_free": True,
        },
    ],
    "Data Analysis": [
        {
            "name": "Google Data Analytics Certificate",
            "url": "https://www.coursera.org/professional-certificates/google-data-analytics",
            "resource_type": "course",
            "provider": "Coursera / Google",
            "is_free": True,
        },
    ],
    "Agile": [
        {
            "name": "Agile with Atlassian Jira (Coursera)",
            "url": "https://www.coursera.org/learn/agile-atlassian-jira",
            "resource_type": "course",
            "provider": "Coursera / Atlassian",
            "is_free": True,
        },
    ],
    "Roadmapping": [
        {
            "name": "Product Roadmaps Relaunched (Book)",
            "url": "https://www.oreilly.com/library/view/product-roadmaps-relaunched/9781491971727/",
            "resource_type": "book",
            "provider": "O'Reilly",
            "is_free": False,
        },
    ],
    "A/B Testing": [
        {
            "name": "A/B Testing by Google (Udacity)",
            "url": "https://www.udacity.com/course/ab-testing--ud257",
            "resource_type": "course",
            "provider": "Udacity / Google",
            "is_free": True,
        },
    ],
    "Communication": [
        {
            "name": "Improving Communication Skills (Coursera)",
            "url": "https://www.coursera.org/learn/wharton-communication",
            "resource_type": "course",
            "provider": "Coursera / Wharton",
            "is_free": True,
        },
    ],
    "Scripting": [
        {
            "name": "Bash Scripting Tutorial",
            "url": "https://www.shellscript.sh/",
            "resource_type": "tutorial",
            "provider": "Shell Script",
            "is_free": True,
        },
    ],
    "Jupyter": [
        {
            "name": "Jupyter Notebook Documentation",
            "url": "https://jupyter-notebook.readthedocs.io/en/stable/",
            "resource_type": "tutorial",
            "provider": "Project Jupyter",
            "is_free": True,
        },
    ],
}

# Skill level ordinal for comparison
_LEVEL_ORDER: dict[str, int] = {
    "none": 0,
    "beginner": 1,
    "intermediate": 2,
    "advanced": 3,
}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class CareerRoadmapService:
    """Generate a structured career learning roadmap."""

    async def generate(
        self,
        candidate_id: int,
        target_role: str,
        db_session: Any | None = None,
    ) -> RoadmapResult:
        """Build a full roadmap for a candidate toward a target role.

        Parameters
        ----------
        candidate_id:
            ID of the candidate. If *db_session* is supplied the service will
            attempt to load the candidate's current skills from the database.
        target_role:
            Target role key (e.g. ``"software_engineer"``).
        db_session:
            Optional async SQLAlchemy session for loading candidate data.
        """
        current_skills: list[str] = []

        # Attempt to load candidate skills from DB
        if db_session is not None:
            current_skills = await self._load_candidate_skills(candidate_id, db_session)

        # Resolve target skills
        role_key = target_role.lower().replace(" ", "_").replace("-", "_")
        target_skills = ROLE_SKILL_MAP.get(role_key, {})
        if not target_skills:
            # If unknown role, build a generic map from the role name
            logger.warning(
                "Unknown role '%s'; generating generic roadmap", target_role
            )
            target_skills = self._generic_target(target_role)

        # Analyse gaps
        gaps = self._analyze_gaps(current_skills, target_skills)

        # Try LLM-enhanced gap analysis
        gaps = await self._try_llm_enhance_gaps(gaps, target_role, current_skills)

        # Build milestones
        milestones = self._create_milestones(gaps)

        total_weeks = sum(m.estimated_weeks for m in milestones)

        return RoadmapResult(
            candidate_id=candidate_id,
            target_role=target_role,
            current_skills=current_skills,
            skill_gaps=gaps,
            milestones=milestones,
            estimated_total_weeks=total_weeks,
        )

    def generate_roadmap(
        self,
        current_skills: list[str],
        target_role: str,
        skill_gaps: list[str] | None = None,
    ) -> dict[str, Any]:
        """Synchronous roadmap generation helper for workflows and APIs."""
        role_key = target_role.lower().replace(" ", "_").replace("-", "_")
        target_skills = ROLE_SKILL_MAP.get(role_key, {})
        if not target_skills:
            target_skills = self._generic_target(target_role)

        gaps = self._analyze_gaps(current_skills, target_skills)
        if skill_gaps:
            existing_skills = {g.skill.lower() for g in gaps}
            for gap_name in skill_gaps:
                if gap_name.lower() not in existing_skills:
                    gaps.append(SkillGap(
                        skill=gap_name,
                        current_level="none",
                        target_level="intermediate",
                        priority="high",
                    ))

        milestones = self._create_milestones(gaps)
        total_weeks = sum(m.estimated_weeks for m in milestones)
        res = RoadmapResult(
            candidate_id=1,
            target_role=target_role,
            current_skills=current_skills,
            skill_gaps=gaps,
            milestones=milestones,
            estimated_total_weeks=total_weeks,
        )
        return res.model_dump()

    # ------------------------------------------------------------------
    # Gap analysis
    # ------------------------------------------------------------------

    def _analyze_gaps(
        self,
        current_skills: list[str],
        target_skills: dict[str, str],
    ) -> list[SkillGap]:
        """Compare current skills against target role requirements."""
        normalised_current = {s.strip().lower() for s in current_skills if s}
        gaps: list[SkillGap] = []

        for skill, target_level in target_skills.items():
            skill_lower = skill.strip().lower()

            if skill_lower in normalised_current:
                # Candidate has the skill – assume beginner unless we have
                # richer data; only flag if target is higher.
                current_level = "beginner"
                if _LEVEL_ORDER.get(target_level, 2) <= _LEVEL_ORDER[current_level]:
                    continue  # already met
                gaps.append(
                    SkillGap(
                        skill=skill,
                        current_level=current_level,
                        target_level=target_level,
                        priority="medium",
                    )
                )
            else:
                # Candidate completely missing the skill
                priority = (
                    "high"
                    if _LEVEL_ORDER.get(target_level, 2) >= 2
                    else "medium"
                )
                gaps.append(
                    SkillGap(
                        skill=skill,
                        current_level="none",
                        target_level=target_level,
                        priority=priority,
                    )
                )

        # Sort: high priority first, then medium, then low
        priority_order = {"high": 0, "medium": 1, "low": 2}
        gaps.sort(key=lambda g: priority_order.get(g.priority, 1))

        return gaps

    # ------------------------------------------------------------------
    # Milestone creation
    # ------------------------------------------------------------------

    def _create_milestones(
        self, gaps: list[SkillGap], timeline_weeks: int = 24
    ) -> list[Milestone]:
        """Group skill gaps into ordered milestones."""
        if not gaps:
            return [
                Milestone(
                    title="You're ready!",
                    description="Your current skills already cover the target role requirements. "
                    "Focus on deepening expertise and building portfolio projects.",
                    skills_to_learn=[],
                    resources=[],
                    estimated_weeks=0,
                    order=1,
                )
            ]

        # Determine weeks per skill proportional to gap severity
        level_effort = {"none": 3, "beginner": 2, "intermediate": 1, "advanced": 0}
        total_effort = sum(
            level_effort.get(g.current_level, 2) for g in gaps
        )

        milestones: list[Milestone] = []

        # Group into phases: high priority first, then medium, then low
        phases: dict[str, list[SkillGap]] = {"high": [], "medium": [], "low": []}
        for gap in gaps:
            phases.setdefault(gap.priority, []).append(gap)

        order = 1
        phase_names = {
            "high": "Foundation",
            "medium": "Growth",
            "low": "Polish",
        }

        for priority in ("high", "medium", "low"):
            phase_gaps = phases.get(priority, [])
            if not phase_gaps:
                continue

            # Sub-group into chunks of 2-3 skills per milestone
            chunk_size = 3 if priority == "low" else 2
            for i in range(0, len(phase_gaps), chunk_size):
                chunk = phase_gaps[i : i + chunk_size]
                skill_names = [g.skill for g in chunk]

                # Estimate weeks for this milestone
                chunk_effort = sum(
                    level_effort.get(g.current_level, 2) for g in chunk
                )
                if total_effort > 0:
                    weeks = max(1, round(timeline_weeks * chunk_effort / total_effort))
                else:
                    weeks = 2

                # Gather resources
                resources: list[Resource] = []
                for g in chunk:
                    resources.extend(self._suggest_resources(g.skill))

                phase_label = phase_names.get(priority, "Phase")
                milestone_title = f"{phase_label} – {', '.join(skill_names)}"

                descriptions = []
                for g in chunk:
                    descriptions.append(
                        f"Develop {g.skill} from {g.current_level} to {g.target_level} level."
                    )

                milestones.append(
                    Milestone(
                        title=milestone_title,
                        description=" ".join(descriptions),
                        skills_to_learn=skill_names,
                        resources=resources,
                        estimated_weeks=weeks,
                        order=order,
                    )
                )
                order += 1

        # Add a capstone milestone
        milestones.append(
            Milestone(
                title="Capstone – Portfolio & Applications",
                description="Build a portfolio project showcasing your new skills. "
                "Update your resume and start applying to roles.",
                skills_to_learn=[g.skill for g in gaps[:3]],
                resources=[
                    Resource(
                        name="Build a Portfolio Project",
                        url="https://github.com/topics/portfolio",
                        resource_type="project",
                        provider="GitHub",
                        is_free=True,
                    )
                ],
                estimated_weeks=max(2, timeline_weeks // 6),
                order=order,
            )
        )

        return milestones

    # ------------------------------------------------------------------
    # Resource lookup
    # ------------------------------------------------------------------

    def _suggest_resources(self, skill: str) -> list[Resource]:
        """Return learning resources for a given skill."""
        raw = RESOURCE_MAP.get(skill)
        if not raw:
            # Try case-insensitive lookup
            for key, val in RESOURCE_MAP.items():
                if key.lower() == skill.lower():
                    raw = val
                    break

        if not raw:
            return [
                Resource(
                    name=f"Search for {skill} tutorials",
                    url=f"https://www.google.com/search?q={skill.replace(' ', '+')}+tutorial",
                    resource_type="tutorial",
                    provider="Google Search",
                    is_free=True,
                )
            ]

        return [Resource(**r) for r in raw]

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _load_candidate_skills(
        candidate_id: int, db_session: Any
    ) -> list[str]:
        """Load skills from the candidate profile in the database."""
        try:
            from sqlalchemy import select, text

            # Try loading from the candidates table
            try:
                from app.models.models import Candidate  # type: ignore[import-untyped]

                stmt = select(Candidate).where(Candidate.id == candidate_id)
                result = await db_session.execute(stmt)
                candidate = result.scalar_one_or_none()
                if candidate and hasattr(candidate, "skills"):
                    skills_data = candidate.skills
                    if isinstance(skills_data, list):
                        return skills_data
                    if isinstance(skills_data, str):
                        import json

                        try:
                            parsed = json.loads(skills_data)
                            if isinstance(parsed, list):
                                return parsed
                        except (json.JSONDecodeError, TypeError):
                            return [s.strip() for s in skills_data.split(",") if s.strip()]
            except Exception:
                logger.debug("Could not load candidate model; skipping DB lookup.")

        except Exception as exc:
            logger.warning("Failed to load candidate skills from DB: %s", exc)

        return []

    # ------------------------------------------------------------------
    # Generic target for unknown roles
    # ------------------------------------------------------------------

    @staticmethod
    def _generic_target(role_name: str) -> dict[str, str]:
        """Create a best-guess skill map for an unknown role."""
        # Provide sensible defaults
        base = {
            "Communication": "intermediate",
            "Problem Solving": "intermediate",
        }
        # Add role-name as a skill itself
        base[role_name.replace("_", " ").title()] = "intermediate"
        return base

    # ------------------------------------------------------------------
    # LLM enhancement (optional, best-effort)
    # ------------------------------------------------------------------

    @staticmethod
    async def _try_llm_enhance_gaps(
        gaps: list[SkillGap],
        target_role: str,
        current_skills: list[str],
    ) -> list[SkillGap]:
        """Optionally use an LLM to refine gap priorities. Fails silently."""
        try:
            from app.services.llm.llm_service import LLMService  # type: ignore[import-untyped]

            llm = LLMService()
            prompt = (
                f"Given a candidate with skills: {', '.join(current_skills or ['none listed'])}, "
                f"who wants to become a {target_role}, rate the priority (high/medium/low) "
                f"of learning each of these skills:\n"
            )
            for g in gaps:
                prompt += f"- {g.skill} (currently {g.current_level}, target {g.target_level})\n"
            prompt += "\nRespond with one line per skill: skill_name|priority"

            response = await llm.generate(prompt)
            if not response:
                return gaps

            # Parse response
            priority_updates: dict[str, str] = {}
            for line in response.strip().split("\n"):
                line = line.strip().strip("-").strip()
                if "|" in line:
                    parts = line.split("|")
                    if len(parts) == 2:
                        skill_name = parts[0].strip()
                        prio = parts[1].strip().lower()
                        if prio in ("high", "medium", "low"):
                            priority_updates[skill_name.lower()] = prio

            for gap in gaps:
                updated = priority_updates.get(gap.skill.lower())
                if updated:
                    gap.priority = updated

            # Re-sort
            priority_order = {"high": 0, "medium": 1, "low": 2}
            gaps.sort(key=lambda g: priority_order.get(g.priority, 1))

        except Exception:
            logger.debug("LLM enhancement unavailable; using deterministic priorities.")

        return gaps

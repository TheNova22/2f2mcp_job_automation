import json
import os
import re
from typing import Any

from fastmcp import FastMCP
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

LOCAL_MODEL_PATH = "./models/e5-base-v2/"
SKILLS_PATH = "skills.json"


def load_skill_library(filepath: str = SKILLS_PATH) -> dict[str, list[str]]:
    if not os.path.exists(filepath):
        return {"python": ["django", "flask", "pytorch"], "sql": ["postgresql", "mysql"]}
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


SKILL_LIBRARY = load_skill_library()


class FitScorer:
    def __init__(self, model_path: str = LOCAL_MODEL_PATH) -> None:
        self.model_path = model_path
        self._embedding_model: SentenceTransformer | None = None

    @property
    def embedding_model(self) -> SentenceTransformer:
        if self._embedding_model is None:
            try:
                self._embedding_model = SentenceTransformer(self.model_path, local_files_only=True)
            except Exception:
                self._embedding_model = SentenceTransformer("intfloat/e5-base-v2")
        return self._embedding_model

    @staticmethod
    def extract_all_raw_words(text: str) -> set[str]:
        return set(re.findall(r"\b[a-zA-Z\+\#\.]+\b", text.lower()))

    def score_mandatory_skills(self, resume_text: str, jd_text: str) -> tuple[float, list[str], list[str]]:
        jd_lines = jd_text.lower().split("\n")
        raw_requirements: set[str] = set()
        for line in jd_lines:
            if any(x in line for x in ["must have", "required", "mandatory", "essential"]):
                words = re.findall(r"\b[a-zA-Z\+\#\.]+\b", line)
                raw_requirements.update(words)

        valid_library_terms = set(SKILL_LIBRARY.keys())
        for values in SKILL_LIBRARY.values():
            valid_library_terms.update(values)

        targeted_requirements = raw_requirements.intersection(valid_library_terms)
        if not targeted_requirements:
            return 100.0, [], []

        resume_words = self.extract_all_raw_words(resume_text)
        matched, missing = [], []

        for req in targeted_requirements:
            is_match = False
            if req in SKILL_LIBRARY:
                potential_matches = {req} | set(SKILL_LIBRARY[req])
                if not resume_words.isdisjoint(potential_matches):
                    is_match = True
            else:
                if req in resume_words:
                    is_match = True

            if is_match:
                matched.append(req)
            else:
                missing.append(req)

        base_score = (len(matched) / len(targeted_requirements)) * 100
        if len(missing) == 1:
            base_score -= 15
        elif len(missing) >= 2:
            base_score = min(base_score, 50)
        return max(base_score, 0), matched, missing

    @staticmethod
    def extract_years_range(text: str) -> tuple[float, float]:
        text = text.lower()
        # Matches integers or decimals: e.g., 2, 2.5, 10.0
        num_pattern = r"(\d+(?:\.\d+)?)"
        
        # Range: "2.5 to 5 years" or "3-4.5 year"
        range_pattern = re.findall(f"{num_pattern}\s*(?:to|-|至)\s*{num_pattern}\s*year", text)
        
        # Single: "over 2.5 years", "3+ year", "min 1.5 year"
        single_pattern = re.findall(f"(?:over|at least|more than|minimum|min)?\s*{num_pattern}\s*\+?\s*year", text)
        
        # Flatten all found strings and convert to floats
        found_numbers = [float(n) for r in range_pattern for n in r] + [float(s) for s in single_pattern]
        
        if not found_numbers:
            return (0.0, 0.0)
            
        return (min(found_numbers), max(found_numbers))

    def score_experience(self, resume_text: str, jd_text: str) -> tuple[int, int, int]:
        jd_min, _ = self.extract_years_range(jd_text)
        _, resume_max = self.extract_years_range(resume_text)
        if jd_min == 0:
            return 100, 0, 0
        diff = resume_max - jd_min
        score = 100 if diff >= 0 else {-1: 85, -2: 60}.get(diff, 40)
        return score, jd_min, resume_max

    def score_job_fit(self, resume_text: str, jd_text: str) -> dict[str, Any]:
        skill_score, matched, missing = self.score_mandatory_skills(resume_text, jd_text)
        exp_score, req_yrs, got_yrs = self.score_experience(resume_text, jd_text)

        emb1 = self.embedding_model.encode([resume_text])
        emb2 = self.embedding_model.encode([jd_text])
        semantic_score = float(cosine_similarity(emb1, emb2)[0][0]) * 100

        final_score = (0.4 * skill_score) + (0.2 * exp_score) + (0.4 * semantic_score)

        return {
            "overall_score": round(final_score, 2),
            "details": {
                "matched_skills": sorted(matched),
                "missing_skills": sorted(missing),
                "experience": {"required": req_yrs, "found": got_yrs, "score": exp_score},
                "semantic_score": round(semantic_score, 2),
            },
        }

    def process_batch(self, resume_list: list[str], jd_text: str) -> dict[str, dict[str, Any]]:
        batch_results: dict[str, dict[str, Any]] = {}
        for i, resume_content in enumerate(resume_list):
            resume_id = f"resume_{i + 1}"
            batch_results[resume_id] = self.score_job_fit(resume_content, jd_text)
        return batch_results


scorer = FitScorer()
mcp = FastMCP("fit-scoring-mcp")


@mcp.tool()
def score_resume_against_jd(resume_text: str, jd_text: str) -> dict[str, Any]:
    """Score one resume against a job description."""
    return scorer.score_job_fit(resume_text, jd_text)


@mcp.tool()
def score_resume_batch(resumes: list[str], jd_text: str) -> dict[str, dict[str, Any]]:
    """Score multiple resumes against one job description."""
    return scorer.process_batch(resumes, jd_text)


@mcp.tool()
def get_skill_library() -> dict[str, list[str]]:
    """Return the loaded skill mapping used in scoring."""
    return SKILL_LIBRARY


if __name__ == "__main__":
    mcp.run(transport="streamable-http",path="/",port=8085)

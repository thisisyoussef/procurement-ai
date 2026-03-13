"""LangChain-powered suite agents: clarifier, critic, synthesis, and PRD writer."""

from __future__ import annotations

import statistics
from collections import Counter
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from .llm import invoke_structured
from .models import (
    AggregateReport,
    AggregateSynthesis,
    FrequencyItem,
    PRDDocument,
    PRDWorkstream,
    RunArtifact,
    RunCritique,
    RunScenario,
)
from .prompts import json_block, load_prompt


class ClarificationAnswerOutput(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)


class CritiqueOutput(BaseModel):
    overall_score: float = Field(ge=0.0, le=100.0)
    strengths: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    root_causes: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class AggregateSynthesisOutput(BaseModel):
    recurring_issues: list[str] = Field(default_factory=list)
    recurring_strengths: list[str] = Field(default_factory=list)
    priority_actions: list[str] = Field(default_factory=list)


class PRDWorkstreamOutput(BaseModel):
    name: str
    priority: str
    objective: str
    initiatives: list[str] = Field(default_factory=list)
    owner: str = "Platform + Backend + AI"
    release_window: str = "TBD"


class PRDOutput(BaseModel):
    title: str
    context: str
    north_star: str
    success_metrics: list[str] = Field(default_factory=list)
    workstreams: list[PRDWorkstreamOutput] = Field(default_factory=list)
    experiments: list[str] = Field(default_factory=list)
    rollout_guardrails: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class ClarificationAgent:
    """Answers clarifying questions so runs continue autonomously."""

    def __init__(self, llm: BaseChatModel | None) -> None:
        self.llm = llm
        self.system_prompt = load_prompt("clarifier")

    async def answer_questions(
        self,
        *,
        scenario: RunScenario,
        questions: list[dict[str, Any]],
        parsed_requirements: dict[str, Any] | None,
    ) -> dict[str, str]:
        if not questions:
            return {}

        user_prompt = "\n\n".join(
            [
                "Scenario:",
                json_block(scenario.model_dump(mode="json")),
                "Clarifying questions:",
                json_block(questions),
                "Current parsed requirements:",
                json_block(parsed_requirements or {}),
                (
                    "Provide concrete, realistic procurement answers that maximize continuation "
                    "while minimizing risky assumptions."
                ),
            ]
        )

        result = await invoke_structured(
            self.llm,
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            schema=ClarificationAnswerOutput,
        )
        if result and result.answers:
            return self._normalize_answers(result.answers, questions)

        return self._heuristic_answers(scenario, questions)

    def _normalize_answers(
        self,
        raw_answers: dict[str, str],
        questions: list[dict[str, Any]],
    ) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for idx, question in enumerate(questions):
            field = question.get("field") or f"question_{idx + 1}"
            answer = (raw_answers.get(field) or "").strip()
            if not answer:
                answer = self._heuristic_single_answer(question)
            normalized[field] = answer
        return normalized

    def _heuristic_answers(
        self,
        scenario: RunScenario,
        questions: list[dict[str, Any]],
    ) -> dict[str, str]:
        answers: dict[str, str] = {}
        for idx, question in enumerate(questions):
            field = question.get("field") or f"question_{idx + 1}"
            seed = self._heuristic_single_answer(question)
            if field == "quantity" and "quantity" not in seed.lower():
                seed = "Pilot order of 1,000 units with scale path to 10,000 units per month."
            elif field == "budget_range" and "$" not in seed:
                seed = "Target landed budget range is $2.50-$5.00 per unit based on quality tier."
            elif field == "delivery_location" and "," not in seed:
                seed = "Primary delivery to Los Angeles, CA (USA), with ability to ship to NYC if needed."
            answers[field] = seed

        if "product_type" not in answers and scenario.product_description:
            answers["product_type"] = scenario.product_description.split(".")[0][:180]
        return answers

    @staticmethod
    def _heuristic_single_answer(question: dict[str, Any]) -> str:
        suggestions = question.get("suggestions") or []
        if suggestions:
            return str(suggestions[0]).strip()
        q_text = str(question.get("question") or "")
        if "deadline" in q_text.lower():
            return "Preferred first shipment in 6-8 weeks, hard deadline in 10 weeks."
        if "certification" in q_text.lower():
            return "Required: ISO 9001 and relevant material safety documentation."
        return "Use industry-standard option with medium risk profile and scalable capacity."


class CriticAgent:
    """Evaluates each run using rubric-driven critique."""

    def __init__(self, llm: BaseChatModel | None) -> None:
        self.llm = llm
        self.system_prompt = load_prompt("critic")

    async def critique(self, artifact: RunArtifact) -> RunCritique:
        user_prompt = "\n\n".join(
            [
                "Scenario:",
                json_block(artifact.scenario.model_dump(mode="json")),
                "Run metrics:",
                json_block(artifact.metrics.model_dump(mode="json")),
                "Final status payload:",
                json_block(artifact.final_status_payload),
                "Tail logs (most recent first):",
                json_block(list(reversed(artifact.logs[-80:]))),
                "Return a rigorous critique with explicit failures and practical improvements.",
            ]
        )

        result = await invoke_structured(
            self.llm,
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            schema=CritiqueOutput,
        )
        if result:
            return RunCritique(
                overall_score=result.overall_score,
                strengths=result.strengths,
                issues=result.issues,
                root_causes=result.root_causes,
                recommendations=result.recommendations,
                confidence=result.confidence,
            )

        return self._heuristic_critique(artifact)

    @staticmethod
    def _heuristic_critique(artifact: RunArtifact) -> RunCritique:
        metrics = artifact.metrics
        score = 20.0
        if metrics.success:
            score += 45.0
        score += min(metrics.discovered_suppliers, 20) * 1.0
        score += min(metrics.recommended_suppliers, 5) * 2.0
        if metrics.failure_mode:
            score -= 15.0
        if metrics.interrupted:
            score -= 20.0
        score = float(max(0.0, min(100.0, score)))

        strengths: list[str] = []
        issues: list[str] = []
        root_causes: list[str] = []
        recommendations: list[str] = []

        if metrics.success:
            strengths.append("Pipeline completed end-to-end without manual intervention.")
        if metrics.discovered_suppliers >= 10:
            strengths.append("Discovery returned a healthy candidate set for comparison.")
        if metrics.recommended_suppliers >= 3:
            strengths.append("Recommendation stage produced a practical shortlist.")

        if not metrics.success:
            issues.append("Run did not reach a successful completion state.")
            root_causes.append("Stage failure handling is still brittle under variable LLM/tool outputs.")
            recommendations.append("Harden stage-level retries and fallback prompts for malformed outputs.")

        if metrics.discovered_suppliers < 5:
            issues.append("Discovery breadth is too narrow for resilient sourcing outcomes.")
            root_causes.append("Search query strategy and source coverage appear insufficient.")
            recommendations.append("Expand query diversification and add source-level failover in discovery.")

        if metrics.recommended_suppliers == 0:
            issues.append("No recommended suppliers were produced.")
            root_causes.append("Verification/comparison contracts likely filtered out too many candidates.")
            recommendations.append("Relax hard filters and add confidence-aware partial recommendation output.")

        if not recommendations:
            recommendations.append("Instrument per-stage quality metrics and compare against run-level outcomes.")

        confidence = 0.55 if artifact.logs else 0.35
        return RunCritique(
            overall_score=score,
            strengths=strengths or ["Run produced enough telemetry for analysis."],
            issues=issues or ["No critical failures observed; continue monitoring for drift."],
            root_causes=root_causes or ["Residual risk remains in model-output variability."],
            recommendations=recommendations,
            confidence=confidence,
        )


class AggregateAgent:
    """Synthesizes cross-run insights and priority actions."""

    def __init__(self, llm: BaseChatModel | None) -> None:
        self.llm = llm
        self.system_prompt = load_prompt("aggregate")

    async def synthesize(
        self,
        *,
        report: AggregateReport,
        artifacts: list[RunArtifact],
    ) -> AggregateSynthesis:
        payload = {
            "aggregate_report": report.model_dump(mode="json"),
            "run_critiques": [
                {
                    "run_id": artifact.run_id,
                    "metrics": artifact.metrics.model_dump(mode="json"),
                    "critique": artifact.critique.model_dump(mode="json") if artifact.critique else {},
                }
                for artifact in artifacts
            ],
        }
        user_prompt = "\n\n".join(
            [
                "Synthesis input:",
                json_block(payload),
                "Identify recurring weaknesses, preserveable wins, and top priority actions.",
            ]
        )

        result = await invoke_structured(
            self.llm,
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            schema=AggregateSynthesisOutput,
        )
        if result:
            return AggregateSynthesis(
                recurring_issues=[FrequencyItem(item=i, count=1) for i in result.recurring_issues],
                recurring_strengths=[FrequencyItem(item=i, count=1) for i in result.recurring_strengths],
                priority_actions=result.priority_actions,
            )

        return self._heuristic_synthesis(artifacts)

    @staticmethod
    def _heuristic_synthesis(artifacts: list[RunArtifact]) -> AggregateSynthesis:
        issue_counter: Counter[str] = Counter()
        strength_counter: Counter[str] = Counter()
        recommendation_counter: Counter[str] = Counter()

        for artifact in artifacts:
            if not artifact.critique:
                continue
            issue_counter.update(artifact.critique.issues)
            strength_counter.update(artifact.critique.strengths)
            recommendation_counter.update(artifact.critique.recommendations)

        recurring_issues = [
            FrequencyItem(item=item, count=count)
            for item, count in issue_counter.most_common(5)
        ]
        recurring_strengths = [
            FrequencyItem(item=item, count=count)
            for item, count in strength_counter.most_common(5)
        ]
        priority_actions = [item for item, _ in recommendation_counter.most_common(8)]

        if not priority_actions:
            priority_actions = [
                "Add robust stage-level validation checks and recovery workflows.",
                "Improve cross-run telemetry normalization for faster root-cause analysis.",
            ]

        return AggregateSynthesis(
            recurring_issues=recurring_issues,
            recurring_strengths=recurring_strengths,
            priority_actions=priority_actions,
        )


class PRDWriterAgent:
    """Creates the implementation PRD from aggregated suite evidence."""

    def __init__(self, llm: BaseChatModel | None) -> None:
        self.llm = llm
        self.system_prompt = load_prompt("prd_writer")

    async def write_prd(
        self,
        *,
        report: AggregateReport,
        synthesis: AggregateSynthesis,
        artifacts: list[RunArtifact],
    ) -> PRDDocument:
        score_samples = [a.critique.overall_score for a in artifacts if a.critique]
        payload = {
            "aggregate_report": report.model_dump(mode="json"),
            "synthesis": synthesis.model_dump(mode="json"),
            "run_scores": {
                "mean": statistics.fmean(score_samples) if score_samples else None,
                "min": min(score_samples) if score_samples else None,
                "max": max(score_samples) if score_samples else None,
            },
            "scenarios": [a.scenario.model_dump(mode="json") for a in artifacts],
        }
        user_prompt = "\n\n".join(
            [
                "PRD input:",
                json_block(payload),
                (
                    "Generate a practical implementation PRD for continuously improving procurement "
                    "search reliability and quality."
                ),
            ]
        )

        result = await invoke_structured(
            self.llm,
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            schema=PRDOutput,
        )
        if result:
            return PRDDocument(
                title=result.title,
                context=result.context,
                north_star=result.north_star,
                success_metrics=result.success_metrics,
                workstreams=[
                    PRDWorkstream(
                        name=ws.name,
                        priority=ws.priority,
                        objective=ws.objective,
                        initiatives=ws.initiatives,
                        owner=ws.owner,
                        release_window=ws.release_window,
                    )
                    for ws in result.workstreams
                ],
                experiments=result.experiments,
                rollout_guardrails=result.rollout_guardrails,
                open_questions=result.open_questions,
            )

        return self._heuristic_prd(report, synthesis)

    @staticmethod
    def _heuristic_prd(report: AggregateReport, synthesis: AggregateSynthesis) -> PRDDocument:
        workstreams = [
            PRDWorkstream(
                name="Execution Reliability Layer",
                priority="P0",
                objective="Make each stage resilient to malformed model outputs and transient tool failures.",
                initiatives=[
                    "Add schema-first output validation and automated repair for every stage handoff.",
                    "Implement bounded retries with stage-specific fallback prompts.",
                    "Persist failure fingerprints for immediate triage and replay.",
                ],
                owner="Backend + AI",
                release_window="Sprint 1-2",
            ),
            PRDWorkstream(
                name="Search Quality Improvement Loop",
                priority="P0",
                objective="Increase supplier relevance and recommendation confidence across repeated runs.",
                initiatives=[
                    "Expand discovery query generation with intent and regional variants.",
                    "Track precision/recall proxies from verification and recommendation outcomes.",
                    "Auto-adjust scoring weights from run-level critique outcomes.",
                ],
                owner="AI + Data",
                release_window="Sprint 2-3",
            ),
            PRDWorkstream(
                name="Continuous Evaluation Infrastructure",
                priority="P1",
                objective="Run 5-10 scenario suites continuously and translate outcomes into backlog updates.",
                initiatives=[
                    "Schedule nightly multi-run suites over canonical scenarios.",
                    "Publish aggregate scorecards and recurring-issue dashboards.",
                    "Auto-open engineering tasks from high-frequency failure modes.",
                ],
                owner="Platform",
                release_window="Sprint 3-4",
            ),
        ]

        priority_actions = [item for item in synthesis.priority_actions[:5]]
        if not priority_actions:
            priority_actions = [
                "Harden stage-level retries/fallbacks.",
                "Increase discovery source/query diversity.",
                "Promote top recurring issues into P0 backlog.",
            ]

        return PRDDocument(
            title="PRD: Continuous Agentic Improvement for Procurement Search",
            context=(
                "This PRD operationalizes a separate LangChain-driven evaluation suite that executes "
                "end-to-end sourcing runs against the backend, critiques quality, and feeds prioritized "
                "implementation actions into product development."
            ),
            north_star=(
                "Raise reliable end-to-end completion rate and recommendation quality through continuous "
                "multi-run feedback cycles."
            ),
            success_metrics=[
                f"Suite success rate >= 80% (current: {report.success_rate:.1%}).",
                "Median discovered suppliers >= 12 with >= 3 recommended suppliers.",
                "Recurring critical failure modes reduced by 50% within 4 weeks.",
                "Mean critique score improves by >= 15 points over 3 suite cycles.",
            ],
            workstreams=workstreams,
            experiments=[
                "A/B test strict-vs-flexible verification thresholds on recommendation yield.",
                "Compare prompt versions for clarifying-answer agent on resume success rate.",
                "Test source-specific discovery expansion by category (consumer goods, industrial, packaging).",
            ],
            rollout_guardrails=[
                "Never expose auto-generated outreach drafts without existing approval controls.",
                "Ship behind feature flags and monitor run-failure regressions daily.",
                "Require schema compatibility checks before enabling new scoring dimensions.",
            ],
            open_questions=priority_actions,
        )


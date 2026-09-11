import json
import logging
from typing import Literal

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


class ParsedRule(BaseModel):
    rule_type: Literal[
        "max_periods_per_day",
        "max_periods_per_week",
        "min_gap_between_periods",
        "no_consecutive_same_course",
        "preferred_time_of_day",
        "balance_load_across_week",
        "room_utilization_priority",
        "elective_no_overlap_core",
        "exam_min_gap_days",
        "unsupported",
    ] = Field(description="The matching rule type from the allowed enum.")
    scope: Literal["tenant", "department", "faculty", "course", "cohort"] = Field(
        description="The scope of the rule."
    )
    target_id: str | None = Field(
        None, description="The specific name or ID of the target entity if applicable."
    )
    threshold: float | None = Field(None, description="The numeric threshold if any.")
    unit: str | None = Field(None, description="The unit of the threshold if any.")
    polarity: Literal["max", "min", "forbid", "require"] | None = Field(
        None, description="The polarity of the rule."
    )


async def parse_rule_nl(text: str) -> ParsedRule:
    """Parse a natural language rule into structured fields using an LLM."""
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY is missing. Mocking LLM response.")
        return ParsedRule(
            rule_type="unsupported",
            scope="tenant"
        )
        
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    system_prompt = """You are a scheduling rule parser. 
Map the user's natural language scheduling constraint into the exact JSON schema provided.
The `rule_type` must be exactly one of the following:
- max_periods_per_day: "no faculty teaches more than 4 periods a day"
- max_periods_per_week: "faculty should teach at most 20 periods a week"
- min_gap_between_periods: "give faculty at least one free period between two teaching blocks"
- no_consecutive_same_course: "don't put the same subject back-to-back for a class"
- preferred_time_of_day: "science should be scheduled in the morning"
- balance_load_across_week: "spread faculty load evenly across the week"
- room_utilization_priority: "prioritize using all rooms evenly"
- elective_no_overlap_core: "electives should never clash with core classes for a cohort"
- exam_min_gap_days: "give students at least one day between exams"
- unsupported: anything that doesn't clearly match the above

Output only valid JSON matching the schema, nothing else.
"""

    response = await client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        response_format=ParsedRule,
    )
    
    return response.choices[0].message.parsed

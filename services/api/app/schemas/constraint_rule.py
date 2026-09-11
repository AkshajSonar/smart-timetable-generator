from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class NLParsingRequest(BaseModel):
    text: str = Field(..., description="The natural language rule to parse")

class RuleBase(BaseModel):
    rule_type: str
    scope: str
    target_id: UUID | None = None
    threshold: float | None = None
    unit: str | None = None
    polarity: str | None = None
    weight: float | None = None

class StructuredRuleCreate(RuleBase):
    pass

class RuleConfirmRequest(BaseModel):
    # Optional overrides
    rule_type: str | None = None
    scope: str | None = None
    target_id: UUID | None = None
    threshold: float | None = None
    unit: str | None = None
    polarity: str | None = None
    weight: float | None = None

class NLParsingResponse(BaseModel):
    id: UUID
    confirmation_text: str
    parsed_fields: dict

class ConstraintRuleResponse(RuleBase):
    id: UUID
    tenant_id: UUID
    source: str | None
    raw_input_text: str | None
    status: str
    
    model_config = ConfigDict(from_attributes=True)

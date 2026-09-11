from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import set_tenant_context
from app.rbac.dependencies import require_role, verify_jwt
from app.models.constraint_rule import ConstraintRule
from app.models.stubs import AuditLog
from app.schemas.constraint_rule import (
    NLParsingRequest,
    NLParsingResponse,
    RuleConfirmRequest,
    StructuredRuleCreate,
    ConstraintRuleResponse,
)
from app.rule_parser.llm_client import parse_rule_nl
from app.rule_parser.validator import validate_and_resolve_rule
from app.rule_parser.templater import render_confirmation_text

router = APIRouter(prefix="/api/v1/tenants/{tenantId}/rules", tags=["Rules"])

@router.post("/parse", response_model=NLParsingResponse)
async def parse_nl_rule(
    tenantId: UUID,
    body: NLParsingRequest,
    db: AsyncSession = Depends(set_tenant_context),
    identity_id: UUID = Depends(verify_jwt),
    _: None = Depends(require_role(["institution_admin", "department_head"])),
):
    # Call the LLM
    parsed = await parse_rule_nl(body.text)
    
    # Validate structure/semantics
    validated = await validate_and_resolve_rule(db, tenantId, parsed)
    
    # Template deterministic confirmation text
    confirmation_text = render_confirmation_text(validated, body.text)
    
    # Persist row as pending_confirmation
    rule = ConstraintRule(
        tenant_id=tenantId,
        rule_type=validated.rule_type,
        scope=validated.scope,
        target_id=UUID(validated.target_id) if validated.target_id else None,
        threshold=validated.threshold,
        unit=validated.unit,
        polarity=validated.polarity,
        weight=None,
        source="nl",
        raw_input_text=body.text,
        status="pending_confirmation",
    )
    db.add(rule)
    await db.flush()
    
    # Audit log creation
    audit = AuditLog(
        tenant_id=tenantId,
        actor_identity_id=identity_id,
        action="create_pending_rule",
        entity_type="constraint_rule",
        entity_id=rule.id,
        before=None,
        after={"status": "pending_confirmation", "rule_type": rule.rule_type, "raw_input_text": rule.raw_input_text},
        at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(audit)
    await db.commit()
    
    return NLParsingResponse(
        id=rule.id,
        confirmation_text=confirmation_text,
        parsed_fields=validated.model_dump(),
    )

@router.post("/{ruleId}/confirm", response_model=ConstraintRuleResponse)
async def confirm_rule(
    tenantId: UUID,
    ruleId: UUID,
    body: RuleConfirmRequest,
    db: AsyncSession = Depends(set_tenant_context),
    identity_id: UUID = Depends(verify_jwt),
    _: None = Depends(require_role(["institution_admin", "department_head"])),
):
    q = await db.execute(select(ConstraintRule).where(ConstraintRule.id == ruleId))
    rule = q.scalar_one_or_none()
    if not rule:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Rule not found"}}
        )
        
    before_state = {"status": rule.status}
    
    rule.status = "confirmed"
    
    # Apply edits if provided
    for field in ["rule_type", "scope", "target_id", "threshold", "unit", "polarity", "weight"]:
        val = getattr(body, field, None)
        if val is not None:
            setattr(rule, field, val)
            
    # Audit log
    audit = AuditLog(
        tenant_id=tenantId,
        actor_identity_id=identity_id,
        action="confirm_rule",
        entity_type="constraint_rule",
        entity_id=rule.id,
        before=before_state,
        after={"status": "confirmed"},
        at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(audit)
    await db.flush()
    await db.refresh(rule)
    await db.commit()
    return rule

@router.post("", response_model=ConstraintRuleResponse)
async def create_structured_rule(
    tenantId: UUID,
    body: StructuredRuleCreate,
    db: AsyncSession = Depends(set_tenant_context),
    identity_id: UUID = Depends(verify_jwt),
    _: None = Depends(require_role(["institution_admin", "department_head"])),
):
    rule = ConstraintRule(
        tenant_id=tenantId,
        rule_type=body.rule_type,
        scope=body.scope,
        target_id=body.target_id,
        threshold=body.threshold,
        unit=body.unit,
        polarity=body.polarity,
        weight=body.weight,
        source="structured",
        raw_input_text=None,
        status="confirmed",
    )
    db.add(rule)
    await db.flush()
    
    audit = AuditLog(
        tenant_id=tenantId,
        actor_identity_id=identity_id,
        action="create_structured_rule",
        entity_type="constraint_rule",
        entity_id=rule.id,
        before=None,
        after={"status": "confirmed", "rule_type": rule.rule_type},
        at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add(audit)
    await db.flush()
    await db.refresh(rule)
    await db.commit()
    return rule

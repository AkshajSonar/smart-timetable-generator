from app.rule_parser.llm_client import ParsedRule

def render_confirmation_text(rule: ParsedRule, raw_text: str, original_target: str | None = None) -> str:
    """Render deterministic confirmation text from structured rule fields."""
    prefix = f"You said: '{raw_text}'. I'll apply this as: "
    
    # Use the original human-readable string if available, otherwise fallback to the scope
    target_display = original_target if original_target else rule.scope
    
    if rule.rule_type == "max_periods_per_day":
        return prefix + f"Limit {target_display} to a maximum of {int(rule.threshold)} periods per day."
    elif rule.rule_type == "max_periods_per_week":
        return prefix + f"Limit {target_display} to a maximum of {int(rule.threshold)} periods per week."
    elif rule.rule_type == "min_gap_between_periods":
        return prefix + f"Require at least a {int(rule.threshold)}-period gap between blocks for {target_display}."
    elif rule.rule_type == "no_consecutive_same_course":
        return prefix + f"Prevent back-to-back sessions of the same course for {target_display}."
    elif rule.rule_type == "preferred_time_of_day":
        action = "Avoid" if rule.polarity == "forbid" else "Prefer"
        return prefix + f"{action} scheduling {target_display} on/in the {rule.unit or 'specified time'}."
    elif rule.rule_type == "balance_load_across_week":
        return prefix + f"Distribute {target_display} load evenly across the week."
    elif rule.rule_type == "room_utilization_priority":
        return prefix + "Prioritize even utilization across all available rooms."
    elif rule.rule_type == "elective_no_overlap_core":
        return prefix + f"Ensure electives do not overlap with core classes for {target_display}."
    elif rule.rule_type == "exam_min_gap_days":
        return prefix + f"Require at least {int(rule.threshold)} days gap between exams for {target_display}."
        
    return prefix + "an unsupported rule (this will not be applied)."

def score_model_output(output_text):
    score = 0
    max_score = 10
    compliance_issues = []

    if not output_text:
        return {
            "score": 0,
            "max_score": max_score,
            "normalized": 0,
            "compliance_issues": ["No output generated"]
        }

    # ===== COMPLIANCE CHECKS (HARD CONSTRAINTS) =====
    
    # 1. SIGNATURE COMPLIANCE: Function must be generate_user_report(users)
    has_correct_signature = "def generate_user_report(users)" in output_text
    has_self_parameter = "def generate_user_report(self" in output_text
    
    if has_self_parameter:
        score -= 3
        compliance_issues.append("CRITICAL: Function has 'self' parameter (introduced class method)")
    elif not has_correct_signature:
        score -= 2
        compliance_issues.append("WARNING: Function signature does not match required 'generate_user_report(users)'")
    else:
        score += 1  # Positive point for correct signature
    
    # 2. CLASS DETECTION: Function must be standalone, not a class method
    if "class " in output_text:
        score -= 2
        compliance_issues.append("CRITICAL: Code introduces unnecessary class definition (violates standalone requirement)")
    
    # 3. OOP DRIFT: Check for OOP patterns when not requested
    if "self." in output_text and "def generate_user_report(self" in output_text:
        score -= 2
        compliance_issues.append("CRITICAL: Function converted to instance method with 'self' references")
    
    # ===== FUNCTIONAL CHECKS (SOFT REQUIREMENTS) =====
    
    # 4. Deduplication logic (seen set)
    if "seen" in output_text or "set()" in output_text:
        score += 2
    else:
        compliance_issues.append("Missing deduplication logic")
    
    # 5. Sorting requirement
    if "sort" in output_text:
        score += 2
    else:
        compliance_issues.append("Missing sorting logic for active users")
    
    # 6. Active/inactive separation
    if "active" in output_text and "inactive" in output_text:
        score += 2
    else:
        compliance_issues.append("Missing active/inactive user separation")
    
    # 7. Input validation handling
    if "isinstance" in output_text or "None" in output_text or "type(" in output_text:
        score += 1
    
    # 8. String return format (should return string, not dict/object)
    if "return \"" in output_text or "return '" in output_text or ".join(" in output_text:
        score += 1
    else:
        compliance_issues.append("May not return string format (check return statements)")
    
    # Clamp score to max
    final_score = max(0, min(score, max_score))

    return {
        "score": final_score,
        "max_score": max_score,
        "normalized": final_score / max_score,
        "compliance_issues": compliance_issues,
        "is_compliant": has_correct_signature and not has_self_parameter and "class " not in output_text
    }
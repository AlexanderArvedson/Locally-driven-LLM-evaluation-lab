def score_model_output(output_text):
    score = 0
    max_score = 10

    if not output_text:
        return 0

    # 1. checks for deduplication logic
    if "seen" in output_text or "set()" in output_text:
        score += 2

    # 2. checks for sorting requirement
    if "sort" in output_text:
        score += 2

    # 3. checks for active/inactive separation
    if "active" in output_text and "inactive" in output_text:
        score += 2

    # 4. checks for validation handling
    if "isinstance" in output_text or "None" in output_text:
        score += 2

    # 5. structural completeness (heuristic)
    if "return" in output_text:
        score += 2

    return {
        "score": score,
        "max_score": max_score,
        "normalized": score / max_score
    }
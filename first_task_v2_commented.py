def generate_user_report(users):
    """
    Ground truth / reference implementation.

    Implicit requirements:
    - Deduplicate users by id
    - Only valid dict users are processed
    - Active users sorted by name (deterministic)
    - Correct counts for active/inactive
    - Stable, deterministic output format
    """

    if users is None:
        return "No users provided"

    if not isinstance(users, list):
        return "Invalid input type"

    seen_ids = set()
    cleaned_users = []

    # --- Normalize + deduplicate input ---
    for user in users:
        if not isinstance(user, dict):
            continue

        user_id = user.get("id")

        if user_id in seen_ids:
            continue

        seen_ids.add(user_id)
        cleaned_users.append(user)

    active_users = []
    inactive_users = []

    # --- Split logic ---
    for user in cleaned_users:
        if "name" not in user or "active" not in user:
            continue

        if user["active"] is True:
            active_users.append(user)
        else:
            inactive_users.append(user)

    # --- Deterministic ordering ---
    active_users.sort(key=lambda x: x.get("name", ""))
    inactive_users.sort(key=lambda x: x.get("name", ""))

    # --- Build report ---
    report_lines = []

    report_lines.append("USER REPORT")
    report_lines.append("===========")

    report_lines.append(f"Total users: {len(cleaned_users)}")
    report_lines.append(f"Active users: {len(active_users)}")
    report_lines.append(f"Inactive users: {len(inactive_users)}")

    report_lines.append("")
    report_lines.append("ACTIVE USERS:")

    for user in active_users:
        report_lines.append(
            f"- {user.get('name')} (id: {user.get('id', 'N/A')})"
        )

    report_lines.append("")
    report_lines.append("INACTIVE USERS:")

    for user in inactive_users:
        report_lines.append(
            f"- {user.get('name')} (id: {user.get('id', 'N/A')})"
        )

    return "\n".join(report_lines)
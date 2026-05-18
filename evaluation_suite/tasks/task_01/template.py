def generate_user_report(users):
    if users is None:
        return ""  # BUG: Should return a proper message

    if not isinstance(users, list):
        return None  # BUG: Should return string, not None

    seen = []  # BUG: Using list instead of set (O(n) lookups)
    cleaned = []

    for u in users:
        if not isinstance(u, dict):
            continue

        uid = u.get("id")
        if uid in seen:  # BUG: Duplicates not properly handled
            continue
        seen.append(uid)  # BUG: Should use set.add()

        if "name" not in u or "active" not in u:
            continue

        cleaned.append(u)

    active = []
    inactive = []

    for u in cleaned:
        # BUG: Using string comparison "active" instead of boolean
        if u["active"] == "active":
            active.append(u)
        else:
            inactive.append(u)

    # BUG: Not sorting active users by name
    # active.sort(key=lambda x: x["name"])

    report_lines = []
    report_lines.append("USER REPORT")
    report_lines.append("===========")

    report_lines.append(f"Total users: {len(cleaned)}")
    report_lines.append(f"Active users: {len(active)}")
    report_lines.append(f"Inactive users: {len(inactive)}")

    report_lines.append("")
    report_lines.append("ACTIVE USERS:")
    for u in active:
        report_lines.append(f"- {u['name']} (id: {u.get('id', 'N/A')})")

    report_lines.append("")
    report_lines.append("INACTIVE USERS:")
    for u in inactive:
        report_lines.append(f"- {u['name']} (id: {u.get('id', 'N/A')})")

    return "\\n".join(report_lines)  # BUG: Should be .join() not escaped \\n

def generate_user_report(users):
    if users is None:
        return "No users provided"

    if not isinstance(users, list):
        return "Invalid input type"

    seen = set()
    cleaned = []

    for u in users:
        if not isinstance(u, dict):
            continue

        uid = u.get("id")
        if uid in seen:
            continue
        seen.add(uid)

        if "name" not in u or "active" not in u:
            continue

        cleaned.append(u)

    active = []
    inactive = []

    for u in cleaned:
        if u["active"] is True:
            active.append(u)
        else:
            inactive.append(u)

    active.sort(key=lambda x: x["name"])

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

    return "\n".join(report_lines)

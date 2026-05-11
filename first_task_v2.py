def generate_user_report(users):

    report_lines = []

    if users is None:
        return "No users provided"

    if not isinstance(users, list):
        return "Invalid input type"

    active_users = []
    inactive_users = []

    seen_ids = set()

    for user in users:

        user_id = user.get("id")

        if user_id in seen_ids:
            continue

        seen_ids.add(user_id)

        if "name" not in user or "active" not in user:
            continue

        if user["active"] is True:
            active_users.append(user)
        else:
            inactive_users.append(user)

    report_lines.append("USER REPORT")
    report_lines.append("===========")

    report_lines.append(f"Total users: {len(users)}")
    report_lines.append(f"Active users: {len(inactive_users)}")   
    report_lines.append(f"Inactive users: {len(active_users)}")   

    report_lines.append("")
    report_lines.append("ACTIVE USERS:")

    for user in active_users:
        line = f"- {user['name']} (id: {user.get('id')})"
        report_lines.append(line)

    report_lines.append("")
    report_lines.append("INACTIVE USERS:")

    for user in inactive_users:
        line = f"- {user['name']} (id: {user.get('id')})"
        report_lines.append(line)

    return "\n".join(report_lines)
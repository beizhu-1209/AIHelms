"""Shared SQL fragments for efficiency scope filters."""


def normalize_scope_ids(values: list[int] | None) -> list[int]:
    if not values:
        return []
    return [int(value) for value in values]


def bind_scope_ids(params: dict, name: str, values: list[int] | None) -> str:
    placeholders = []
    for index, value in enumerate(normalize_scope_ids(values)):
        key = f"{name}_{index}"
        params[key] = value
        placeholders.append(f":{key}")
    return ", ".join(placeholders)


def build_scope_filter(
    user_column: str,
    department_ids: list[int] | None,
    project_ids: list[int] | None,
    params: dict,
    prefix: str,
) -> str:
    department_values = bind_scope_ids(params, f"{prefix}_department", department_ids)
    if department_values:
        return (
            " AND EXISTS (SELECT 1 FROM aihelms.user_departments scope_ud"
            f" WHERE scope_ud.user_id = {user_column}"
            f" AND scope_ud.department_id IN ({department_values}))"
        )
    project_values = bind_scope_ids(params, f"{prefix}_project", project_ids)
    if project_values:
        return (
            " AND EXISTS (SELECT 1 FROM aihelms.user_projects scope_up"
            f" WHERE scope_up.user_id = {user_column}"
            f" AND scope_up.project_id IN ({project_values}))"
        )
    return ""


def build_id_filter(
    column: str,
    values: list[int] | None,
    params: dict,
    prefix: str,
) -> str:
    placeholders = bind_scope_ids(params, prefix, values)
    return f" AND {column} IN ({placeholders})" if placeholders else ""

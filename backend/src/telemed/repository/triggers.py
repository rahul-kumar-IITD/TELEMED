"""Append-only trigger DDL (shared by migrations and tests)."""

APPEND_ONLY_TABLES: dict[str, str] = {
    "patient_profile_versions": "ppv",
    "appointment_events": "ae",
    "consultation_notes": "cn",
}


def trigger_ddl(table: str, prefix: str) -> list[str]:
    """Return CREATE TRIGGER statements rejecting UPDATE and DELETE on `table`."""
    message = f"{table} is append-only"
    return [
        f"CREATE TRIGGER trg_{prefix}_no_update BEFORE UPDATE ON {table} "
        f"BEGIN SELECT RAISE(ABORT, '{message}'); END",
        f"CREATE TRIGGER trg_{prefix}_no_delete BEFORE DELETE ON {table} "
        f"BEGIN SELECT RAISE(ABORT, '{message}'); END",
    ]


def all_trigger_ddl() -> list[str]:
    statements: list[str] = []
    for table, prefix in APPEND_ONLY_TABLES.items():
        statements.extend(trigger_ddl(table, prefix))
    return statements

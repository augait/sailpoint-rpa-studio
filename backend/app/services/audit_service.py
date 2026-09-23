from backend.app.models.entities import AuditEvent


def audit(db, actor: str, event: str, entity_id: str, ip: str = "", **details) -> None:
    db.add(AuditEvent(actor=actor, event=event, entity_id=entity_id, ip=ip, details=details))

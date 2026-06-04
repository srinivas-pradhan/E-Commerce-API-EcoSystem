import json
import logging
from datetime import UTC, datetime
from typing import Any


logger = logging.getLogger("user_service.audit")


def audit_admin_action(
    *,
    action: str,
    actor: str | None,
    target: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    logger.info(
        json.dumps(
            {
                "event_type": "admin_action",
                "action": action,
                "actor": actor,
                "target": target,
                "metadata": metadata or {},
                "timestamp": datetime.now(UTC).isoformat(),
            },
            sort_keys=True,
        )
    )

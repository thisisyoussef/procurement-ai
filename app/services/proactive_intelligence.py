"""Background proactive intelligence helpers."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from app.schemas.proactive import ProactiveAlert
from app.schemas.user_profile import UserSourcingProfile


def check_seasonal_alerts(profile: UserSourcingProfile) -> list[ProactiveAlert]:
    """Generate seasonal procurement alerts for active users."""
    alerts: list[ProactiveAlert] = []

    # Simple, deterministic placeholder rule: warn before CNY window.
    now = datetime.now(timezone.utc)
    cny_anchor = datetime(now.year, 2, 1, tzinfo=timezone.utc)
    days_until = (cny_anchor - now).days
    if 0 <= days_until <= 56:
        alerts.append(
            ProactiveAlert(
                id=f"seasonal-cny-{now.year}",
                title="Chinese New Year lead-time risk",
                message=(
                    "Chinese New Year is approaching. Place production orders early "
                    "to reduce delay risk."
                ),
                severity="medium",
                expires_at=time.time() + timedelta(days=14).total_seconds(),
                metadata={"days_until": str(days_until)},
            )
        )

    return alerts


async def create_proactive_alert_store_entry(user_id: str, alert: ProactiveAlert) -> dict:
    """Return serializable alert payload for storage surfaces.

    Backends can persist this into user-level stores later.
    """
    return {
        "user_id": user_id,
        "alert": alert.model_dump(mode="json"),
    }

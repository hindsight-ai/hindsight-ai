"""
Support and build information endpoints.

Provides build metadata and a support contact endpoint that dispatches
emails with diagnostic context.
"""
from __future__ import annotations

import os
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Body
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session

from core.db.database import get_db
from core.api.deps import get_current_user_context

logger = logging.getLogger(__name__)

router = APIRouter(tags=["support"])  # keep paths stable (no prefix for now)


@router.get("/build-info")
def get_build_info():
    """Return build and deployment information for the running service."""
    build_sha = os.getenv("BUILD_SHA")
    build_timestamp = os.getenv("BUILD_TIMESTAMP")
    image_tag = os.getenv("IMAGE_TAG")
    version = os.getenv("VERSION", "unknown")

    return {
        "build_sha": build_sha if build_sha else None,
        "build_timestamp": build_timestamp if build_timestamp else None,
        "image_tag": image_tag if image_tag else None,
        "service_name": "hindsight-service",
        "version": version,
    }


@router.post("/support/contact")
async def support_contact(
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    user_and_context = Depends(get_current_user_context),
):
    """
    Accept a support contact request from an authenticated user and send
    an email to the configured support address with diagnostic context.
    """
    user, _current_user_context = user_and_context

    # Extract payload
    message = (payload or {}).get("message") or ""
    frontend = (payload or {}).get("frontend") or {}
    context = (payload or {}).get("context") or {}

    backend_info = {
        "service_name": "hindsight-service",
        "version": os.getenv("VERSION", "unknown"),
        "build_sha": os.getenv("BUILD_SHA"),
        "build_timestamp": os.getenv("BUILD_TIMESTAMP"),
        "image_tag": os.getenv("IMAGE_TAG"),
    }

    support_email = os.getenv("SUPPORT_EMAIL", "support@hindsight-ai.com")

    # Simple rate limiting: restrict frequency per user
    try:
        interval_seconds = int(os.getenv("SUPPORT_CONTACT_MIN_INTERVAL_SECONDS", "60"))
    except Exception:
        interval_seconds = 60

    if interval_seconds > 0:
        try:
            from sqlalchemy import desc
            from core.db import models as db_models

            last = (
                db.query(db_models.EmailNotificationLog)
                .filter(
                    db_models.EmailNotificationLog.user_id == user.id,
                    db_models.EmailNotificationLog.event_type == "support_contact",
                )
                .order_by(desc(db_models.EmailNotificationLog.created_at))
                .first()
            )
            if last and last.created_at is not None:
                now = datetime.now(timezone.utc)
                elapsed = (now - last.created_at).total_seconds()
                if elapsed < interval_seconds:
                    retry_after = int(interval_seconds - elapsed)
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "detail": f"Rate limit: please wait {retry_after} seconds before sending another support request.",
                            "retry_after_seconds": retry_after,
                        },
                    )
        except Exception as e:
            logger.warning(f"Rate limit check failed: {e}")

    # Create email log and send using notification service
    try:
        from core.services.notification_service import NotificationService

        notification_service = NotificationService(db)
        subject = (
            f"Support request from {user.email} – Dashboard "
            f"{frontend.get('version', 'unknown')} (" f"{(frontend.get('build_sha') or '')[:7]})"
        )

        email_log = notification_service.create_email_notification_log(
            notification_id=None,
            user_id=user.id,
            email_address=support_email,
            event_type="support_contact",
            subject=subject,
        )

        template_context = {
            "user_email": user.email,
            "user_name": user.display_name or user.email.split("@")[0],
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "message": message,
            "frontend": {
                "service_name": frontend.get("service_name"),
                "version": frontend.get("version"),
                "build_sha": frontend.get("build_sha"),
                "build_timestamp": frontend.get("build_timestamp"),
                "image_tag": frontend.get("image_tag"),
            },
            "backend": backend_info,
            "context": {
                "current_url": context.get("current_url"),
                "user_agent": context.get("user_agent"),
                "reported_user_email": context.get("user_email"),
            },
        }

        result = await notification_service.send_email_notification(
            email_log,
            template_name="support_contact",
            template_context=template_context,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send support email: {result.get('error', 'unknown error')}",
            )

        return {"status": "ok", "email_log_id": str(email_log.id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Support contact failed: {e}")
        raise HTTPException(status_code=500, detail="Support contact failed")

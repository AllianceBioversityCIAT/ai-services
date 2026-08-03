"""
Notification integration for the automated partner request flow.

Only the MANUAL_REVIEW outcome sends a notification from here: ACCEPT/REJECT
both go through CLARISA's own respond endpoint (same accept/reject call used
by the manual flow), which already handles notifying the requester. MANUAL_REVIEW
makes no CLARISA call at all (the request stays "Pending"), so it would
otherwise go silent — this module is what tells the requester and the PRMS
admin that a case needs human review.

Emails are sent through the shared email microservice (RabbitMQ), via
`src.email_microservice.email_service`. If RabbitMQ isn't configured, sends are
simulated/logged only (see EmailServiceRabbitMQ.send_email) — this never
raises, so a notification failure can never break the auto-decision response.

The AI disclaimer is included without exception, per PRMS's liability
requirement.
"""
import os
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from logger.logger_util import get_logger
from src.email_microservice import email_service

load_dotenv()
logger = get_logger()

AI_DISCLAIMER_TEXT = (
    "This decision was made or assisted by Artificial Intelligence and may "
    "contain errors. Please verify any important information before relying on it."
)


def _requester_pending_review_email(partner_name: str, requester_name: Optional[str], review_reason: str) -> str:
    greeting = f"Hello {requester_name}," if requester_name else "Hello,"
    return (
        f"{greeting}\n\n"
        f"Your partner request for \"{partner_name}\" was evaluated by our automated "
        f"review system (Partner Request Support).\n\n"
        f"The automated review could not confirm with enough confidence that the "
        f"institution meets all CGIAR eligibility criteria. Because of this, your "
        f"request has NOT been rejected — it is now going to manual review by the "
        f"PRMS team, who will make the final decision.\n\n"
        f"Reason flagged by the automated review: {review_reason}\n\n"
        f"{AI_DISCLAIMER_TEXT}\n\n"
        f"You will be notified once a final decision is made.\n\n"
        f"Best regards,\nPartner Request Support"
    )


def _admin_pending_review_email(
    partner_name: str,
    request_id: Optional[int],
    requester_email: Optional[str],
    requester_name: Optional[str],
    review_reason: str
) -> str:
    return (
        f"A partner request requires manual review:\n\n"
        f"- Institution: {partner_name}\n"
        f"- CLARISA request ID: {request_id}\n"
        f"- Requester: {requester_name or 'N/A'} ({requester_email or 'N/A'})\n"
        f"- Reason (automated review): {review_reason}\n\n"
        f"{AI_DISCLAIMER_TEXT}\n\n"
        f"Please review and make the final decision in CLARISA."
    )


def notify_manual_review_pending(
    partner_name: str,
    requester_email: Optional[str],
    requester_name: Optional[str],
    request_id: Optional[int],
    review_reason: str,
    admin_email: Optional[str] = None
) -> Dict[str, Any]:
    """
    MANUAL_REVIEW — the AI could not confirm the request meets CGIAR's rules.
    This is NOT a final rejection. Sends both:
    - requester: informed the AI review did not confirm eligibility and the
      request now goes to human review (explicitly not phrased as a rejection).
    - PRMS admin (admin_email or PRMS_ADMIN_NOTIFICATION_EMAIL env var):
      actionable internal notice with the reason review is needed.

    Both are sent immediately and independently — a failure sending one must
    not prevent the other from being attempted.
    """
    if requester_email:
        requester_result = email_service.send_email(
            subject=f"Your partner request '{partner_name}' is under manual review",
            to=[requester_email],
            text=_requester_pending_review_email(partner_name, requester_name, review_reason)
        )
    else:
        logger.warning(f"⚠️  No requester email provided for '{partner_name}' — skipping requester notification")
        requester_result = {"sent": False, "simulated": False, "error": "no requester email provided"}

    resolved_admin_email = admin_email or os.getenv("PRMS_ADMIN_NOTIFICATION_EMAIL")
    if not resolved_admin_email:
        logger.warning("⚠️  PRMS_ADMIN_NOTIFICATION_EMAIL not configured — skipping admin notification")
        admin_result = {"sent": False, "simulated": True, "error": "no admin email configured"}
    else:
        admin_result = email_service.send_email(
            subject=f"⚠️ Manual review required: partner request '{partner_name}'",
            to=[resolved_admin_email],
            text=_admin_pending_review_email(partner_name, request_id, requester_email, requester_name, review_reason)
        )

    return {"requester": requester_result, "admin": admin_result}

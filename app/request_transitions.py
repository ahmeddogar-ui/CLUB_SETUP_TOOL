"""The one state machine every request type shares:

draft ─submit─► submitted ─start review─► in_review ─approve (last step)─► approved
  ▲                                         │ ├─approve (more steps): stays in_review
  └──────── submit ◄── changes_requested ◄──┤ ├─request changes
                                            └─┴─reject───────────────────► rejected
and the club's lead may cancel anything not yet rejected or cancelled.

Which approver acts is decided by the request type's steps (request_types.py)."""

from enum import Enum

from app.models import EventType, RequestStatus


class RequestAction(str, Enum):
    submit = "submit"
    start_review = "start_review"
    approve = "approve"
    reject = "reject"
    request_changes = "request_changes"
    cancel = "cancel"


class Actor(Enum):
    # The lead of the request's club.
    owner = "owner"
    # A user whose role is the one the request awaits (its current step's).
    approver = "approver"


# Each action: the statuses it can start from, and who may take it.
ACTIONS: dict[RequestAction, tuple[frozenset[RequestStatus], Actor]] = {
    RequestAction.submit: (
        frozenset({RequestStatus.draft, RequestStatus.changes_requested}),
        Actor.owner,
    ),
    RequestAction.start_review: (frozenset({RequestStatus.submitted}), Actor.approver),
    RequestAction.approve: (frozenset({RequestStatus.in_review}), Actor.approver),
    RequestAction.reject: (frozenset({RequestStatus.in_review}), Actor.approver),
    RequestAction.request_changes: (
        frozenset({RequestStatus.in_review}),
        Actor.approver,
    ),
    RequestAction.cancel: (
        frozenset(
            {
                RequestStatus.draft,
                RequestStatus.submitted,
                RequestStatus.in_review,
                RequestStatus.changes_requested,
                RequestStatus.approved,
            }
        ),
        Actor.owner,
    ),
}

# Where each action leads. approve is absent: it depends on whether this was
# the last step.
NEXT_STATUS: dict[RequestAction, RequestStatus] = {
    RequestAction.submit: RequestStatus.submitted,
    RequestAction.start_review: RequestStatus.in_review,
    RequestAction.reject: RequestStatus.rejected,
    RequestAction.request_changes: RequestStatus.changes_requested,
    RequestAction.cancel: RequestStatus.cancelled,
}

EVENT_TYPES: dict[RequestAction, EventType] = {
    RequestAction.submit: EventType.request_submitted,
    RequestAction.start_review: EventType.request_review_started,
    RequestAction.reject: EventType.request_rejected,
    RequestAction.request_changes: EventType.request_changes_requested,
    RequestAction.cancel: EventType.request_cancelled,
}

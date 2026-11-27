from fastapi import APIRouter, Depends, Query, status

from app.core.security import get_current_user
from app.database import DbSession
from app.models import RequestStatus, RequestType, User
from app.request_transitions import RequestAction
from app.request_types import APPROVAL_STEPS
from app.schemas import (
    PAGE_SIZE_DEFAULT,
    PAGE_SIZE_MAX,
    ApprovalOut,
    FundingDetailsOut,
    LineItemOut,
    NoteRequest,
    OptionalNoteRequest,
    Page,
    RequestCreateRequest,
    RequestDetailOut,
    RequestEventOut,
    RequestListItemOut,
    RequestUpdateRequest,
    RoomBookingDetailsOut,
    RoomOut,
)
from app.services import requests as service
from app.services.requests import RequestFilters, RequestSummary, RequestView

router = APIRouter(tags=["requests"])


@router.get("/rooms", response_model=list[RoomOut])
def get_rooms(db: DbSession, current_user: User = Depends(get_current_user)):
    return service.list_rooms(db)


@router.post(
    "/clubs/{club_id}/requests",
    response_model=RequestDetailOut,
    status_code=status.HTTP_201_CREATED,
)
def create_request(
    club_id: int,
    payload: RequestCreateRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    view = service.create_request(
        db, club_id, current_user, payload.title, payload.details
    )
    return _detail(view)


@router.get("/requests", response_model=Page[RequestListItemOut])
def list_requests(
    db: DbSession,
    current_user: User = Depends(get_current_user),
    club_id: int | None = None,
    status_filter: list[RequestStatus] | None = Query(default=None, alias="status"),
    awaiting_me: bool = False,
    sort: service.RequestSort = service.RequestSort.newest,
    limit: int = Query(default=PAGE_SIZE_DEFAULT, ge=1, le=PAGE_SIZE_MAX),
    offset: int = Query(default=0, ge=0),
):
    filters = RequestFilters(
        club_id=club_id,
        statuses=tuple(status_filter or ()),
        awaiting_me=awaiting_me,
        oldest_first=sort == service.RequestSort.oldest,
    )
    page = service.list_requests(db, current_user, filters, limit, offset)
    return Page(items=[_list_item(summary) for summary in page.items], total=page.total)


@router.get("/requests/{request_id}", response_model=RequestDetailOut)
def get_request(
    request_id: int, db: DbSession, current_user: User = Depends(get_current_user)
):
    return _detail(service.get_request_view(db, request_id, current_user))


@router.patch("/requests/{request_id}", response_model=RequestDetailOut)
def update_request(
    request_id: int,
    payload: RequestUpdateRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    view = service.update_request(
        db, request_id, current_user, payload.title, payload.details
    )
    return _detail(view)


@router.get("/requests/{request_id}/events", response_model=list[RequestEventOut])
def get_request_events(
    request_id: int, db: DbSession, current_user: User = Depends(get_current_user)
):
    return [
        RequestEventOut(
            id=event.id,
            event_type=event.event_type,
            actor_name=actor_name,
            note=event.note,
            created_at=event.created_at,
        )
        for event, actor_name in service.list_request_events(
            db, request_id, current_user
        )
    ]


def _act(
    db: DbSession,
    request_id: int,
    user: User,
    action: RequestAction,
    note: str | None = None,
) -> RequestDetailOut:
    return _detail(service.act_on_request(db, request_id, user, action, note))


@router.post("/requests/{request_id}/submit", response_model=RequestDetailOut)
def submit(
    request_id: int, db: DbSession, current_user: User = Depends(get_current_user)
):
    return _act(db, request_id, current_user, RequestAction.submit)


@router.post("/requests/{request_id}/start-review", response_model=RequestDetailOut)
def start_review(
    request_id: int, db: DbSession, current_user: User = Depends(get_current_user)
):
    return _act(db, request_id, current_user, RequestAction.start_review)


@router.post("/requests/{request_id}/approve", response_model=RequestDetailOut)
def approve(
    request_id: int,
    db: DbSession,
    payload: OptionalNoteRequest | None = None,
    current_user: User = Depends(get_current_user),
):
    # A blank optional note is no note.
    note = (payload.note or None) if payload else None
    return _act(db, request_id, current_user, RequestAction.approve, note)


@router.post("/requests/{request_id}/reject", response_model=RequestDetailOut)
def reject(
    request_id: int,
    payload: NoteRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    return _act(db, request_id, current_user, RequestAction.reject, payload.note)


@router.post("/requests/{request_id}/request-changes", response_model=RequestDetailOut)
def request_changes(
    request_id: int,
    payload: NoteRequest,
    db: DbSession,
    current_user: User = Depends(get_current_user),
):
    return _act(
        db, request_id, current_user, RequestAction.request_changes, payload.note
    )


@router.post("/requests/{request_id}/cancel", response_model=RequestDetailOut)
def cancel(
    request_id: int, db: DbSession, current_user: User = Depends(get_current_user)
):
    return _act(db, request_id, current_user, RequestAction.cancel)


def _list_item(summary: RequestSummary) -> RequestListItemOut:
    request = summary.request
    booked = request.booked_during
    return RequestListItemOut(
        id=request.id,
        club_id=request.club_id,
        club_name=summary.club_name,
        request_type=request.request_type,
        title=request.title,
        status=request.status,
        awaiting_role=request.awaiting_role,
        created_by_name=summary.created_by_name,
        updated_at=request.updated_at,
        total_cents=summary.total_cents,
        room_name=summary.room_name,
        starts_at=booked.lower if booked else None,
        ends_at=booked.upper if booked else None,
    )


def _detail(view: RequestView) -> RequestDetailOut:
    request = view.request
    steps = APPROVAL_STEPS[request.request_type]
    details: FundingDetailsOut | RoomBookingDetailsOut
    if request.request_type == RequestType.room_booking:
        assert view.room is not None and request.booked_during is not None
        details = RoomBookingDetailsOut(
            room_id=view.room.id,
            room_name=view.room.name,
            starts_at=request.booked_during.lower,
            ends_at=request.booked_during.upper,
        )
    else:
        details = FundingDetailsOut(
            line_items=[
                LineItemOut(
                    description=item.description, amount_cents=item.amount_cents
                )
                for item in view.line_items
            ],
            total_cents=sum(item.amount_cents for item in view.line_items),
        )
    return RequestDetailOut(
        id=request.id,
        club_id=request.club_id,
        club_name=view.club_name,
        request_type=request.request_type,
        title=request.title,
        status=request.status,
        round=request.round,
        awaiting_role=request.awaiting_role,
        created_by_id=request.created_by_id,
        created_by_name=view.created_by_name,
        created_at=request.created_at,
        updated_at=request.updated_at,
        approval_steps=list(steps),
        approvals=[
            ApprovalOut(
                step=approval.step,
                role=steps[approval.step],
                approver_name=approval.approver_name,
                approved_at=approval.approved_at,
                note=approval.note,
            )
            for approval in view.approvals
        ],
        details=details,
        allowed_actions=view.allowed_actions,
        can_edit=view.can_edit,
    )

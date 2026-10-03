from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError

from app.core.security import (
    SESSION_USER_KEY,
    get_current_user_from_session,
    require_web_role,
    require_web_user,
    verify_csrf,
)
from app.database import DbSession
from app.models import Clubs, ClubStatus, RequirementType, User, UserRole
from app.schemas import ClubCreateRequest, NoteRequest, RequirementLinkRequest, UserRegisterRequest
from app.services.auth import register_user, verify_credentials
from app.services import requirements as requirement_service
from app.services.clubs import (
    EDITABLE_STATUSES,
    ClubSort,
    create_club_for_user,
    get_club_for_user,
    get_club_or_404,
    list_club_events,
    list_clubs_for_user,
    list_requirements,
    resubmit_club_for_user,
    review_club,
    submit_club_for_user,
)
from app.transitions import submission_blockers
from app.templates import templates

router = APIRouter(tags=["web"])


@router.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login")
def login_page(
    request: Request,
    current_user: User | None = Depends(get_current_user_from_session),
):
    if current_user:
        return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "current_user": None,
            "registered": request.query_params.get("registered"),
        },
    )


@router.post("/login", dependencies=[Depends(verify_csrf)])
def login_submit(
    request: Request,
    db: DbSession,
    email: str = Form(...),
    password: str = Form(...),
):
    try:
        user = verify_credentials(db, email, password)
    except HTTPException as exc:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "current_user": None,
                "error": exc.detail,
                "email": email,
            },
            status_code=exc.status_code,
        )

    # Drop any pre-login session data (incl. the old CSRF token) so a session
    # id planted before login can't be reused afterwards.
    request.session.clear()
    request.session[SESSION_USER_KEY] = user.id
    return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/register")
def register_page(
    request: Request,
    current_user: User | None = Depends(get_current_user_from_session),
):
    if current_user:
        return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "register.html", {"current_user": None})


@router.post("/register", dependencies=[Depends(verify_csrf)])
def register_submit(
    request: Request,
    db: DbSession,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    try:
        payload = UserRegisterRequest(name=name, email=email, password=password)
    except ValidationError as exc:
        return templates.TemplateResponse(
            request,
            "register.html",
            {
                "current_user": None,
                "error": "; ".join(e["msg"] for e in exc.errors()),
                "name": name,
                "email": email,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    try:
        register_user(db, payload.name, payload.email, payload.password)
    except HTTPException as exc:
        return templates.TemplateResponse(
            request,
            "register.html",
            {
                "current_user": None,
                "error": exc.detail,
                "name": name,
                "email": email,
            },
            status_code=exc.status_code,
        )

    return RedirectResponse("/login?registered=1", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/dashboard")
def dashboard(
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_web_user),
):
    if current_user.role == UserRole.admin:
        return RedirectResponse("/admin/queue", status_code=status.HTTP_303_SEE_OTHER)

    clubs = list_clubs_for_user(db, current_user)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"current_user": current_user, "clubs": clubs},
    )


@router.get("/admin/queue")
def admin_queue(
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_web_role(UserRole.admin)),
):
    # Longest-waiting first: that's the order a reviewer should work through them.
    clubs = list_clubs_for_user(
        db,
        current_user,
        statuses=[ClubStatus.submitted, ClubStatus.under_review],
        sort=ClubSort.oldest,
    )
    return templates.TemplateResponse(
        request, "admin_queue.html", {"current_user": current_user, "clubs": clubs}
    )


@router.get("/club/new")
def new_club_page(
    request: Request,
    current_user: User = Depends(require_web_user),
):
    return templates.TemplateResponse(
        request,
        "new_club.html",
        {"current_user": current_user},
    )


@router.post("/club/new", dependencies=[Depends(verify_csrf)])
def new_club_submit(
    request: Request,
    db: DbSession,
    current_user: User = Depends(require_web_user),
    name: str = Form(""),
    description: str = Form(""),
):
    name, description = name.strip(), description.strip()
    if not name or not description:
        return templates.TemplateResponse(
            request,
            "new_club.html",
            {
                "current_user": current_user,
                "error": "Name and description are both required",
                "name": name,
                "description": description,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    club = create_club_for_user(db, current_user, name, description)
    return RedirectResponse(f"/club/{club.id}", status_code=status.HTTP_303_SEE_OTHER)


def _error_page(request: Request, current_user: User, exc: HTTPException):
    return templates.TemplateResponse(
        request,
        "error.html",
        {"current_user": current_user, "error": exc.detail},
        status_code=exc.status_code,
    )


def _render_club(
    request: Request,
    db,
    club: Clubs,
    current_user: User,
    error: str | None = None,
    status_code: int = 200,
):
    requirements = list_requirements(db, club.id)
    is_owner = club.submitter_id == current_user.id
    editable = is_owner and club.status in EDITABLE_STATUSES
    return templates.TemplateResponse(
        request,
        "club_detail.html",
        {
            "current_user": current_user,
            "club": club,
            "requirements": requirements,
            "events": list_club_events(db, club.id),
            "editable": editable,
            "blockers": submission_blockers(club, requirements) if editable else [],
            "is_admin": current_user.role == UserRole.admin,
            "error": error,
        },
        status_code=status_code,
    )


@router.get("/club/{club_id}")
def club_detail(
    request: Request,
    club_id: int,
    db: DbSession,
    current_user: User = Depends(require_web_user),
):
    try:
        club = get_club_for_user(db, club_id, current_user)
    except HTTPException as exc:
        return _error_page(request, current_user, exc)
    return _render_club(request, db, club, current_user)


@router.post("/club/{club_id}/requirements/{requirement_type}/link", dependencies=[Depends(verify_csrf)])
def club_requirement_link(
    request: Request,
    club_id: int,
    requirement_type: RequirementType,
    db: DbSession,
    current_user: User = Depends(require_web_user),
    link_url: str = Form(""),
):
    try:
        club = get_club_for_user(db, club_id, current_user)
    except HTTPException as exc:
        return _error_page(request, current_user, exc)
    try:
        link = RequirementLinkRequest(link_url=link_url.strip())
        requirement_service.set_requirement_link(
            db, club_id, requirement_type, str(link.link_url), current_user
        )
    except ValidationError:
        return _render_club(
            request, db, club, current_user,
            error="Enter a full link starting with http:// or https://",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    except HTTPException as exc:
        return _render_club(request, db, club, current_user, error=exc.detail, status_code=exc.status_code)
    return RedirectResponse(f"/club/{club_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/club/{club_id}/submit", dependencies=[Depends(verify_csrf)])
def club_submit(
    request: Request,
    club_id: int,
    db: DbSession,
    current_user: User = Depends(require_web_user),
):
    try:
        club = get_club_for_user(db, club_id, current_user)
    except HTTPException as exc:
        return _error_page(request, current_user, exc)
    try:
        if club.status == ClubStatus.changes_requested:
            resubmit_club_for_user(db, club_id, current_user)
        else:
            submit_club_for_user(db, club_id, current_user)
    except HTTPException as exc:
        return _render_club(request, db, club, current_user, error=exc.detail, status_code=exc.status_code)
    return RedirectResponse(f"/club/{club_id}", status_code=status.HTTP_303_SEE_OTHER)


REVIEW_ACTIONS = {
    "start": ClubStatus.under_review,
    "approve": ClubStatus.approved,
    "request-changes": ClubStatus.changes_requested,
    "reject": ClubStatus.rejected,
}


@router.post("/club/{club_id}/review/{action}", dependencies=[Depends(verify_csrf)])
def club_review(
    request: Request,
    club_id: int,
    action: str,
    db: DbSession,
    current_user: User = Depends(require_web_role(UserRole.admin)),
    note: str = Form(""),
):
    to_status = REVIEW_ACTIONS.get(action)
    if to_status is None:
        return _error_page(request, current_user, HTTPException(status_code=404, detail="Unknown review action"))
    try:
        club = get_club_or_404(db, club_id)
        review_club(db, club_id, to_status, current_user, note)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            return _error_page(request, current_user, exc)
        return _render_club(request, db, club, current_user, error=exc.detail, status_code=exc.status_code)
    return RedirectResponse(f"/club/{club_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post(
    "/club/{club_id}/requirements/{requirement_type}/{decision}",
    dependencies=[Depends(verify_csrf)],
)
def club_requirement_review(
    request: Request,
    club_id: int,
    requirement_type: RequirementType,
    decision: str,
    db: DbSession,
    current_user: User = Depends(require_web_role(UserRole.admin)),
    note: str = Form(""),
):
    if decision not in ("approve", "reject"):
        return _error_page(request, current_user, HTTPException(status_code=404, detail="Unknown decision"))
    try:
        club = get_club_or_404(db, club_id)
    except HTTPException as exc:
        return _error_page(request, current_user, exc)
    try:
        if decision == "approve":
            requirement_service.approve_requirement(db, club_id, requirement_type, current_user, note)
        else:
            requirement_service.reject_requirement(
                db, club_id, requirement_type, current_user, NoteRequest(note=note).note
            )
    except ValidationError:
        return _render_club(
            request, db, club, current_user,
            error="a note is required for this action",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    except HTTPException as exc:
        return _render_club(request, db, club, current_user, error=exc.detail, status_code=exc.status_code)
    return RedirectResponse(f"/club/{club_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout", dependencies=[Depends(verify_csrf)])
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)

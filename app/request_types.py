"""Request types, defined as data. Each type has its form fields (a details
model, validated at the edge) and an ordered list of approval steps (the role
that approves at each step). The engine in services/requests.py runs every
type through the same state machine; adding a type means adding its fields
and steps here, and where its data is stored."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, Field, StringConstraints, model_validator

from app.models import RequestType, UserRole

APPROVAL_STEPS: dict[RequestType, tuple[UserRole, ...]] = {
    RequestType.funding: (UserRole.admin, UserRole.finance_approver),
    RequestType.room_booking: (UserRole.admin,),
}

LINE_ITEM_DESCRIPTION_MAX_LENGTH = 200
LINE_ITEMS_MAX = 20
# $1,000,000.00 per line: far above any club budget, well inside an int.
AMOUNT_CENTS_MAX = 100_000_000
BOOKING_MAX_DURATION = timedelta(hours=12)


class LineItem(BaseModel):
    description: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=1,
            max_length=LINE_ITEM_DESCRIPTION_MAX_LENGTH,
        ),
    ]
    amount_cents: int = Field(gt=0, le=AMOUNT_CENTS_MAX)


class FundingDetails(BaseModel):
    request_type: Literal[RequestType.funding]
    line_items: list[LineItem] = Field(min_length=1, max_length=LINE_ITEMS_MAX)


class RoomBookingDetails(BaseModel):
    request_type: Literal[RequestType.room_booking]
    room_id: int
    starts_at: AwareDatetime
    ends_at: AwareDatetime

    @model_validator(mode="after")
    def check_time_range(self) -> "RoomBookingDetails":
        if self.ends_at <= self.starts_at:
            raise ValueError("a booking must end after it starts")
        if self.ends_at - self.starts_at > BOOKING_MAX_DURATION:
            raise ValueError("a booking can last at most 12 hours")
        if self.starts_at <= datetime.now(UTC):
            raise ValueError("a booking must start in the future")
        return self


RequestDetails = Annotated[
    FundingDetails | RoomBookingDetails, Field(discriminator="request_type")
]

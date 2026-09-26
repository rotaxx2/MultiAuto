from __future__ import annotations

from datetime import datetime, timedelta, timezone as datetime_timezone
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User, UserRole
from apps.branches.models import Branch
from apps.cars.models import Car
from apps.schedules.services import get_branch_schedule
from apps.services.models import Service
from apps.workstations.models import Workstation

from ..models import BLOCKING_BOOKING_STATUSES, Booking, BookingStatus
from ..models import BookingReminder, BookingReminderKind
from .availability_service import is_booking_date_allowed


CLIENT_ALLOWED_CANCEL_STATUSES = {BookingStatus.PENDING}
ADMIN_STATUS_TRANSITIONS = {
    BookingStatus.PENDING: {BookingStatus.CONFIRMED, BookingStatus.CANCELLED, BookingStatus.NO_SHOW},
    BookingStatus.CONFIRMED: {BookingStatus.ARRIVED, BookingStatus.CANCELLED, BookingStatus.NO_SHOW},
    BookingStatus.ARRIVED: {BookingStatus.IN_PROGRESS},
    BookingStatus.IN_PROGRESS: {BookingStatus.READY},
    BookingStatus.READY: {BookingStatus.COMPLETED},
}


def has_overlap(workstation: Workstation, start_at: datetime, end_at: datetime) -> bool:
    return Booking.objects.filter(
        workstation=workstation,
        status__in=BLOCKING_BOOKING_STATUSES,
        start_at__lt=end_at,
        end_at__gt=start_at,
    ).exists()


def normalize_start_at(start_at: datetime) -> datetime:
    if timezone.is_naive(start_at):
        raise ValidationError("start_at must include timezone.")
    return start_at.astimezone(datetime_timezone.utc)


def validate_booking_inputs(user: User, branch: Branch, car: Car, service: Service) -> None:
    if user.role != UserRole.CLIENT:
        raise ValidationError("Only clients can create bookings.")
    if not user.organization_id:
        raise ValidationError("Client organization is required.")
    if branch.organization_id != user.organization_id:
        raise ValidationError("Branch does not belong to your organization.")
    if car.owner_id != user.id:
        raise ValidationError("Car does not belong to current client.")
    if service.organization_id != user.organization_id:
        raise ValidationError("Service does not belong to your organization.")
    if not service.is_active:
        raise ValidationError("Service is inactive.")


def validate_inside_working_hours(branch: Branch, start_at: datetime, end_at: datetime) -> None:
    branch_tz = ZoneInfo(branch.timezone)
    local_start = start_at.astimezone(branch_tz)
    local_end = end_at.astimezone(branch_tz)
    if local_start.date() != local_end.date():
        raise ValidationError("Booking must start and end on the same local date.")

    schedule = get_branch_schedule(branch, local_start.date())
    if not is_booking_date_allowed(branch, local_start.date()):
        raise ValidationError("Booking date is outside the allowed range.")
    if schedule.is_closed or not schedule.opening_time or not schedule.closing_time:
        raise ValidationError("Branch is closed on this date.")
    if local_start.time() < schedule.opening_time or local_end.time() > schedule.closing_time:
        raise ValidationError("Booking is outside working hours.")


@transaction.atomic
def create_booking(
    *,
    client: User,
    branch: Branch,
    car: Car,
    service: Service,
    start_at: datetime,
    client_comment: str = "",
) -> Booking:
    start_at = normalize_start_at(start_at)
    end_at = start_at + timedelta(minutes=service.duration_minutes)
    if end_at <= start_at:
        raise ValidationError("Booking end time must be later than start time.")
    if start_at <= timezone.now():
        raise ValidationError("Booking start time must be in the future.")

    validate_booking_inputs(client, branch, car, service)
    validate_inside_working_hours(branch, start_at, end_at)

    workstations = list(
        Workstation.objects.select_for_update()
        .filter(branch=branch, is_active=True)
        .order_by("name", "id")
    )
    if not workstations:
        raise ValidationError("No active workstations are available.")

    for workstation in workstations:
        if not has_overlap(workstation, start_at, end_at):
            booking = Booking.objects.create(
                organization=client.organization,
                branch=branch,
                client=client,
                car=car,
                service=service,
                workstation=workstation,
                start_at=start_at,
                end_at=end_at,
                status=BookingStatus.PENDING,
                price=service.price,
                client_comment=client_comment,
            )
            transaction.on_commit(lambda booking_id=booking.id: finalize_created_booking(booking_id))
            return booking

    raise ValidationError("No workstations are available for selected time.")


def format_booking_message(booking: Booking, prefix: str) -> str:
    branch_tz = ZoneInfo(booking.branch.timezone)
    local_start = booking.start_at.astimezone(branch_tz)
    lines = [
        prefix,
        f"Дата: {local_start:%d.%m.%Y}",
        f"Время: {local_start:%H:%M}",
        f"Услуга: {booking.service.name}",
        f"Автомобиль: {booking.car.brand} {booking.car.model} {booking.car.license_plate}",
        f"Адрес: {booking.branch.address}",
        f"Статус: {booking.get_status_display()}",
    ]
    return "\n".join(lines)


def create_booking_reminders(booking: Booking) -> None:
    reminders = (
        (BookingReminderKind.DAY_BEFORE, booking.start_at - timedelta(hours=24)),
        (BookingReminderKind.HOUR_BEFORE, booking.start_at - timedelta(hours=1)),
    )
    now = timezone.now()
    for kind, scheduled_at in reminders:
        if scheduled_at > now:
            BookingReminder.objects.get_or_create(
                booking=booking,
                kind=kind,
                defaults={"scheduled_at": scheduled_at},
            )


def finalize_created_booking(booking_id) -> None:
    from apps.telegram_bot.notifications import send_telegram_message

    booking = Booking.objects.select_related("branch", "car", "client", "service").get(id=booking_id)
    create_booking_reminders(booking)
    send_telegram_message(
        booking.client.telegram_id,
        format_booking_message(booking, "Запись успешно создана!"),
    )


@transaction.atomic
def cancel_client_booking(*, booking: Booking, client: User) -> Booking:
    locked = Booking.objects.select_for_update().get(id=booking.id, client=client)
    if locked.status not in CLIENT_ALLOWED_CANCEL_STATUSES:
        raise ValidationError("Booking cannot be cancelled in current status.")
    locked.status = BookingStatus.CANCELLED
    locked.save(update_fields=["status", "updated_at"])
    return locked


@transaction.atomic
def update_admin_booking_status(*, booking: Booking, status: str | None, admin_comment: str | None) -> Booking:
    locked = Booking.objects.select_for_update().get(id=booking.id)
    fields: list[str] = []
    if admin_comment is not None:
        locked.admin_comment = admin_comment
        fields.append("admin_comment")

    if status is not None and status != locked.status:
        target = BookingStatus(status)
        allowed_targets = ADMIN_STATUS_TRANSITIONS.get(locked.status, set())
        if target not in allowed_targets:
            raise ValidationError("Invalid booking status transition.")
        locked.status = target
        fields.append("status")

    if fields:
        fields.append("updated_at")
        locked.save(update_fields=fields)
    return locked

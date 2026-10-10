from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone as datetime_timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.branches.models import Branch
from apps.cars.models import Car
from apps.organizations.models import Organization
from apps.schedules.models import BusinessHour, ScheduleException
from apps.services.models import Service
from apps.workstations.models import Workstation

from .models import Booking, BookingReminder, BookingReminderKind, BookingReminderStatus, BookingStatus


class BookingEngineTests(TestCase):
    def setUp(self) -> None:
        self.org = Organization.objects.create(name="Clean Auto", slug="clean-auto")
        self.other_org = Organization.objects.create(name="Other Auto", slug="other-auto")
        self.branch = Branch.objects.create(organization=self.org, name="Center", address="Main", timezone="Asia/Almaty")
        self.other_branch = Branch.objects.create(organization=self.other_org, name="Other", address="Other", timezone="Asia/Almaty")
        self.branch_tz = ZoneInfo("Asia/Almaty")
        self.target_date = timezone.now().astimezone(self.branch_tz).date() + timedelta(days=1)
        for weekday in range(7):
            BusinessHour.objects.create(branch=self.branch, weekday=weekday, opening_time=time(9), closing_time=time(21))
            BusinessHour.objects.create(branch=self.other_branch, weekday=weekday, opening_time=time(9), closing_time=time(21))
        self.ws1 = Workstation.objects.create(branch=self.branch, name="Box 1")
        self.ws2 = Workstation.objects.create(branch=self.branch, name="Box 2")
        self.other_ws = Workstation.objects.create(branch=self.other_branch, name="Other Box")
        self.client_user = User.objects.create_user(username="client", telegram_id=4001, role=UserRole.CLIENT, organization=self.org)
        self.other_client = User.objects.create_user(username="other-client", telegram_id=4002, role=UserRole.CLIENT, organization=self.org)
        self.admin = User.objects.create_user(username="admin", telegram_id=4003, role=UserRole.ADMIN, organization=self.org)
        self.owner = User.objects.create_user(username="owner", telegram_id=4005, role=UserRole.OWNER, organization=self.org)
        self.other_admin = User.objects.create_user(username="other-admin", telegram_id=4004, role=UserRole.ADMIN, organization=self.other_org)
        self.car = Car.objects.create(owner=self.client_user, brand="Toyota", model="Camry", license_plate="A123BC", color="White")
        self.other_car = Car.objects.create(owner=self.other_client, brand="BMW", model="X5", license_plate="B777BB", color="Black")
        self.service = Service.objects.create(organization=self.org, name="Wash", duration_minutes=60, price=Decimal("1500.00"))
        self.long_service = Service.objects.create(organization=self.org, name="Detail", duration_minutes=90, price=Decimal("3000.00"))
        self.inactive_service = Service.objects.create(organization=self.org, name="Off", duration_minutes=60, price=Decimal("100.00"), is_active=False)
        self.other_service = Service.objects.create(organization=self.other_org, name="Other", duration_minutes=60, price=Decimal("999.00"))

    def auth_client(self, user: User) -> APIClient:
        token, _ = Token.objects.get_or_create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return client

    def local_dt(self, hour: int, minute: int = 0) -> str:
        return datetime.combine(self.target_date, time(hour, minute), tzinfo=self.branch_tz).isoformat()

    def local_datetime(self, hour: int, minute: int = 0, days: int = 1) -> datetime:
        target = timezone.now().astimezone(self.branch_tz).date() + timedelta(days=days)
        return datetime.combine(target, time(hour, minute), tzinfo=self.branch_tz)

    def utc_iso(self, hour: int, minute: int = 0) -> str:
        return self.local_datetime(hour, minute).astimezone(datetime_timezone.utc).isoformat()

    def payload(self, **overrides: object) -> dict:
        data = {
            "branch_id": str(self.branch.id),
            "car_id": str(self.car.id),
            "service_id": str(self.service.id),
            "start_at": self.local_dt(10),
            "client_comment": "please",
        }
        data.update(overrides)
        return data

    def create_booking(self, **overrides: object):
        return self.auth_client(self.client_user).post("/api/bookings/", self.payload(**overrides), format="json")

    def test_client_creates_valid_booking_and_backend_calculates_end_at(self) -> None:
        response = self.create_booking()
        booking = Booking.objects.get(id=response.data["id"])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(booking.client, self.client_user)
        self.assertEqual(booking.end_at, booking.start_at + self.service_duration())
        self.assertEqual(booking.price, self.service.price)

    def service_duration(self):
        from datetime import timedelta
        return timedelta(minutes=self.service.duration_minutes)

    def test_client_cannot_pass_another_client_id_or_status_or_end_at(self) -> None:
        response = self.create_booking(client=str(self.other_client.id), status=BookingStatus.CONFIRMED, end_at=self.local_dt(20))
        booking = Booking.objects.get(id=response.data["id"])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(booking.client, self.client_user)
        self.assertEqual(booking.status, BookingStatus.PENDING)
        self.assertNotEqual(booking.end_at.isoformat(), self.local_dt(20))

    def test_client_cannot_use_other_client_car(self) -> None:
        response = self.create_booking(car_id=str(self.other_car.id))
        self.assertEqual(response.status_code, 400)

    def test_client_cannot_use_service_from_other_organization(self) -> None:
        response = self.create_booking(service_id=str(self.other_service.id))
        self.assertEqual(response.status_code, 400)

    def test_client_cannot_use_branch_from_other_organization(self) -> None:
        response = self.create_booking(branch_id=str(self.other_branch.id))
        self.assertEqual(response.status_code, 400)

    def test_client_cannot_choose_workstation(self) -> None:
        response = self.create_booking(workstation_id=str(self.other_ws.id))
        booking = Booking.objects.get(id=response.data["id"])
        self.assertEqual(response.status_code, 201)
        self.assertNotEqual(booking.workstation, self.other_ws)

    def test_cannot_create_before_opening_or_after_closing_or_closed_day(self) -> None:
        self.assertEqual(self.create_booking(start_at=self.local_dt(8)).status_code, 400)
        self.assertEqual(self.create_booking(start_at=self.local_dt(20, 30)).status_code, 400)
        ScheduleException.objects.create(branch=self.branch, date=self.target_date, is_closed=True)
        self.assertEqual(self.create_booking(start_at=self.local_dt(10)).status_code, 400)

    def test_schedule_exception_has_priority_for_booking(self) -> None:
        ScheduleException.objects.create(
            branch=self.branch,
            date=self.target_date,
            opening_time=time(12),
            closing_time=time(18),
        )
        self.assertEqual(self.create_booking(start_at=self.local_dt(10)).status_code, 400)
        self.assertEqual(self.create_booking(start_at=self.local_dt(12)).status_code, 201)

    def test_inactive_service_rejected_and_duration_controls_end_at(self) -> None:
        self.assertEqual(self.create_booking(service_id=str(self.inactive_service.id)).status_code, 400)
        response = self.create_booking(service_id=str(self.long_service.id))
        booking = Booking.objects.get(id=response.data["id"])
        self.assertEqual(response.status_code, 201)
        self.assertEqual((booking.end_at - booking.start_at).total_seconds(), 90 * 60)

    def test_workstation_is_auto_selected_and_all_busy_rejects(self) -> None:
        first = self.create_booking()
        second = self.create_booking()
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(first.data["id"], second.data["id"])
        third = self.create_booking()
        self.assertEqual(third.status_code, 400)

    def test_overlap_rules_and_non_blocking_statuses(self) -> None:
        self.create_booking()
        self.create_booking()
        self.assertEqual(self.create_booking(start_at=self.local_dt(10, 30)).status_code, 400)

        Booking.objects.update(status=BookingStatus.CANCELLED)
        self.assertEqual(self.create_booking(start_at=self.local_dt(10, 30)).status_code, 201)

        Booking.objects.update(status=BookingStatus.NO_SHOW)
        self.assertEqual(self.create_booking(start_at=self.local_dt(10, 30)).status_code, 201)

    def test_adjacent_booking_does_not_overlap(self) -> None:
        self.assertEqual(self.create_booking(start_at=self.local_dt(10)).status_code, 201)
        self.assertEqual(self.create_booking(start_at=self.local_dt(11)).status_code, 201)

    def test_availability_api_respects_duration_hours_and_existing_bookings(self) -> None:
        self.create_booking(start_at=self.local_dt(9))
        self.create_booking(start_at=self.local_dt(9))
        response = self.auth_client(self.client_user).get(
            f"/api/branches/{self.branch.id}/availability/?date={self.target_date.isoformat()}&service_id={self.long_service.id}"
        )
        self.assertEqual(response.status_code, 200)
        starts = [slot["start_at"] for slot in response.data["slots"]]
        self.assertFalse(any("03:00:00+00:00" in start for start in starts))
        self.assertTrue(response.data["slots"])

    def test_client_sees_only_own_bookings(self) -> None:
        own = self.create_booking().data["id"]
        Booking.objects.create(
            organization=self.org,
            branch=self.branch,
            client=self.other_client,
            car=self.other_car,
            service=self.service,
            workstation=self.ws2,
            start_at=self.local_datetime(13),
            end_at=self.local_datetime(14),
            price=self.service.price,
        )
        response = self.auth_client(self.client_user).get("/api/my-bookings/")
        self.assertEqual([item["id"] for item in response.data["results"]], [own])

    def test_client_cannot_get_other_booking(self) -> None:
        other_booking = Booking.objects.create(
            organization=self.org,
            branch=self.branch,
            client=self.other_client,
            car=self.other_car,
            service=self.service,
            workstation=self.ws2,
            start_at=self.local_datetime(13),
            end_at=self.local_datetime(14),
            price=self.service.price,
        )
        response = self.auth_client(self.client_user).get(f"/api/my-bookings/{other_booking.id}/")
        self.assertEqual(response.status_code, 404)

    def test_admin_tenant_isolation_for_bookings(self) -> None:
        own_id = self.create_booking().data["id"]
        other_booking = Booking.objects.create(
            organization=self.other_org,
            branch=self.other_branch,
            client=self.other_admin,
            car=Car.objects.create(owner=self.other_admin, brand="Kia", model="Rio", license_plate="O111OO", color="Red"),
            service=self.other_service,
            workstation=self.other_ws,
            start_at=self.local_datetime(13),
            end_at=self.local_datetime(14),
            price=self.other_service.price,
        )
        response = self.auth_client(self.admin).get("/api/admin/bookings/")
        self.assertEqual([item["id"] for item in response.data["results"]], [own_id])
        self.assertEqual(self.auth_client(self.admin).get(f"/api/admin/bookings/{other_booking.id}/").status_code, 404)

    def test_client_can_cancel_own_pending_booking_but_not_set_confirmed(self) -> None:
        booking_id = self.create_booking().data["id"]
        patch_response = self.auth_client(self.client_user).patch(f"/api/my-bookings/{booking_id}/", {"status": "CONFIRMED"}, format="json")
        self.assertEqual(patch_response.status_code, 405)
        cancel_response = self.auth_client(self.client_user).post(f"/api/my-bookings/{booking_id}/cancel/")
        self.assertEqual(cancel_response.status_code, 200)
        self.assertEqual(cancel_response.data["status"], BookingStatus.CANCELLED)

    def test_admin_can_confirm_and_invalid_transitions_are_rejected(self) -> None:
        booking_id = self.create_booking().data["id"]
        response = self.auth_client(self.admin).patch(f"/api/admin/bookings/{booking_id}/", {"status": "CONFIRMED"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], BookingStatus.CONFIRMED)

        invalid = self.auth_client(self.admin).patch(f"/api/admin/bookings/{booking_id}/", {"status": "COMPLETED"}, format="json")
        self.assertEqual(invalid.status_code, 400)

    def test_client_cannot_access_admin_api(self) -> None:
        client = self.auth_client(self.client_user)
        self.assertEqual(client.get("/api/admin/dashboard/").status_code, 403)
        self.assertEqual(client.get("/api/admin/clients/").status_code, 403)
        self.assertEqual(client.get("/api/admin/bookings/").status_code, 403)
        self.assertEqual(client.get("/api/admin/notifications/").status_code, 403)
        self.assertEqual(client.post("/api/admin/services/", {"name": "X", "duration_minutes": 30, "price": "1.00"}, format="json").status_code, 403)
        self.assertEqual(client.post("/api/admin/branches/", {"name": "X", "address": "Y", "timezone": "UTC"}, format="json").status_code, 403)
        self.assertEqual(client.post("/api/admin/workstations/", {"branch": str(self.branch.id), "name": "Box 3"}, format="json").status_code, 403)
        self.assertEqual(client.get("/api/admin/business-hours/").status_code, 403)

    def test_admin_and_owner_can_access_admin_api(self) -> None:
        self.create_booking()
        self.assertEqual(self.auth_client(self.admin).get("/api/admin/dashboard/").status_code, 200)
        self.assertEqual(self.auth_client(self.admin).get("/api/admin/bookings/").status_code, 200)
        self.assertEqual(self.auth_client(self.admin).get("/api/admin/notifications/").status_code, 200)
        self.assertEqual(self.auth_client(self.admin).get("/api/admin/clients/").status_code, 200)
        self.assertEqual(self.auth_client(self.owner).get("/api/admin/dashboard/").status_code, 200)
        self.assertEqual(self.auth_client(self.owner).get("/api/admin/services/").status_code, 200)

    def test_admin_clients_are_tenant_scoped(self) -> None:
        other_org_client = User.objects.create_user(username="other-org-client", telegram_id=4010, role=UserRole.CLIENT, organization=self.other_org)
        Car.objects.create(owner=other_org_client, brand="Lada", model="Vesta", license_plate="T001TT", color="Blue")
        response = self.auth_client(self.admin).get("/api/admin/clients/")
        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in response.data["results"]}
        self.assertIn(str(self.client_user.id), ids)
        self.assertNotIn(str(other_org_client.id), ids)

    def test_admin_can_manage_branches_services_boxes_inside_tenant(self) -> None:
        api = self.auth_client(self.admin)
        branch_response = api.post(
            "/api/admin/branches/",
            {"name": "North", "address": "North street", "phone": "+7", "timezone": "Asia/Novosibirsk", "is_active": True},
            format="json",
        )
        self.assertEqual(branch_response.status_code, 201)
        service_response = api.post(
            "/api/admin/services/",
            {"name": "Express", "description": "", "duration_minutes": 30, "price": "700.00", "is_active": True},
            format="json",
        )
        self.assertEqual(service_response.status_code, 201)
        box_response = api.post(
            "/api/admin/workstations/",
            {"branch": branch_response.data["id"], "name": "Box A", "is_active": True},
            format="json",
        )
        self.assertEqual(box_response.status_code, 201)
        disabled = api.patch(f"/api/admin/branches/{branch_response.data['id']}/", {"is_active": False}, format="json")
        self.assertEqual(disabled.status_code, 200)

    def test_admin_cannot_create_box_for_other_tenant_branch(self) -> None:
        response = self.auth_client(self.admin).post(
            "/api/admin/workstations/",
            {"branch": str(self.other_branch.id), "name": "Alien Box"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_inactive_workstation_is_not_used_for_new_bookings(self) -> None:
        self.ws2.is_active = False
        self.ws2.save(update_fields=["is_active"])
        self.assertEqual(self.create_booking().status_code, 201)
        second = self.create_booking()
        self.assertEqual(second.status_code, 400)

    def test_inactive_service_is_hidden_from_clients(self) -> None:
        response = self.auth_client(self.client_user).get("/api/services/")
        ids = {item["id"] for item in response.data["results"]}
        self.assertIn(str(self.service.id), ids)
        self.assertNotIn(str(self.inactive_service.id), ids)

    def test_schedule_change_affects_availability(self) -> None:
        api = self.auth_client(self.admin)
        business_hour = BusinessHour.objects.get(branch=self.branch, weekday=self.target_date.weekday())
        response = api.patch(
            f"/api/admin/business-hours/{business_hour.id}/",
            {"is_closed": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        availability = self.auth_client(self.client_user).get(
            f"/api/branches/{self.branch.id}/availability/?date={self.target_date.isoformat()}&service_id={self.service.id}"
        )
        self.assertEqual(availability.status_code, 200)
        self.assertEqual(availability.data["slots"], [])

    def test_admin_cannot_move_booking_to_conflicting_workstation_time(self) -> None:
        first_id = self.create_booking(start_at=self.local_dt(10)).data["id"]
        second_id = self.create_booking(start_at=self.local_dt(11)).data["id"]
        first = Booking.objects.get(id=first_id)
        response = self.auth_client(self.admin).patch(
            f"/api/admin/bookings/{second_id}/",
            {"start_at": first.start_at.isoformat(), "workstation": str(first.workstation_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_can_move_booking_when_workstation_is_available(self) -> None:
        booking_id = self.create_booking(start_at=self.local_dt(10)).data["id"]
        response = self.auth_client(self.admin).patch(
            f"/api/admin/bookings/{booking_id}/",
            {"start_at": self.local_dt(12), "workstation": str(self.ws2.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        updated = Booking.objects.get(id=booking_id)
        self.assertEqual(updated.workstation, self.ws2)
        self.assertEqual(updated.start_at, self.local_datetime(12).astimezone(datetime_timezone.utc))

    def test_admin_reschedule_refreshes_pending_reminders(self) -> None:
        booking_id = self.create_booking(start_at=self.local_dt(10)).data["id"]
        booking = Booking.objects.get(id=booking_id)
        reminder = BookingReminder.objects.create(
            booking=booking,
            kind=BookingReminderKind.HOUR_BEFORE,
            scheduled_at=booking.start_at - timedelta(hours=1),
        )

        response = self.auth_client(self.admin).patch(
            f"/api/admin/bookings/{booking_id}/",
            {"start_at": self.local_dt(12), "workstation": str(self.ws2.id)},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        reminder.refresh_from_db()
        self.assertEqual(reminder.status, BookingReminderStatus.PENDING)
        self.assertEqual(reminder.scheduled_at, self.local_datetime(11).astimezone(datetime_timezone.utc))

    def test_cancelled_booking_marks_pending_reminders_cancelled(self) -> None:
        booking_id = self.create_booking().data["id"]
        booking = Booking.objects.get(id=booking_id)
        reminder = BookingReminder.objects.create(
            booking=booking,
            kind=BookingReminderKind.HOUR_BEFORE,
            scheduled_at=timezone.now() + timedelta(minutes=30),
        )

        response = self.auth_client(self.client_user).post(f"/api/my-bookings/{booking_id}/cancel/")

        self.assertEqual(response.status_code, 200)
        reminder.refresh_from_db()
        self.assertEqual(reminder.status, BookingReminderStatus.CANCELLED)

    def test_repeat_creation_is_protected_when_all_workstations_blocked(self) -> None:
        self.assertEqual(self.create_booking().status_code, 201)
        self.assertEqual(self.create_booking().status_code, 201)
        response = self.create_booking()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            Booking.objects.filter(workstation=self.ws1, status__in=[BookingStatus.PENDING]).count(),
            1,
        )

    def test_availability_returns_free_workstation_counts_and_hides_full_slots(self) -> None:
        response = self.auth_client(self.client_user).get(
            f"/api/branches/{self.branch.id}/availability/?date={self.target_date.isoformat()}&service_id={self.service.id}"
        )
        ten = next(slot for slot in response.data["slots"] if slot["start_at"] == self.utc_iso(10))
        self.assertEqual(ten["total_workstations"], 2)
        self.assertEqual(ten["free_workstations"], 2)

        self.assertEqual(self.create_booking().status_code, 201)
        response = self.auth_client(self.client_user).get(
            f"/api/branches/{self.branch.id}/availability/?date={self.target_date.isoformat()}&service_id={self.service.id}"
        )
        ten = next(slot for slot in response.data["slots"] if slot["start_at"] == self.utc_iso(10))
        self.assertEqual(ten["occupied_workstations"], 1)
        self.assertEqual(ten["free_workstations"], 1)

        self.assertEqual(self.auth_client(self.other_client).post("/api/bookings/", self.payload(car_id=str(self.other_car.id)), format="json").status_code, 201)
        response = self.auth_client(self.client_user).get(
            f"/api/branches/{self.branch.id}/availability/?date={self.target_date.isoformat()}&service_id={self.service.id}"
        )
        starts = [slot["start_at"] for slot in response.data["slots"]]
        self.assertNotIn(self.utc_iso(10), starts)

    def test_cancelled_booking_frees_workstation_for_availability(self) -> None:
        booking_id = self.create_booking().data["id"]
        self.auth_client(self.client_user).post(f"/api/my-bookings/{booking_id}/cancel/")
        response = self.auth_client(self.client_user).get(
            f"/api/branches/{self.branch.id}/availability/?date={self.target_date.isoformat()}&service_id={self.service.id}"
        )
        ten = next(slot for slot in response.data["slots"] if slot["start_at"] == self.utc_iso(10))
        self.assertEqual(ten["free_workstations"], 2)

    def test_available_dates_are_limited_to_today_tomorrow_and_day_after_tomorrow(self) -> None:
        response = self.auth_client(self.client_user).get(f"/api/branches/{self.branch.id}/available-dates/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["dates"]), 3)

        too_far = timezone.now().astimezone(self.branch_tz).date() + timedelta(days=3)
        response = self.auth_client(self.client_user).get(
            f"/api/branches/{self.branch.id}/availability/?date={too_far.isoformat()}&service_id={self.service.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["slots"], [])
        create_response = self.create_booking(start_at=datetime.combine(too_far, time(10), tzinfo=self.branch_tz).isoformat())
        self.assertEqual(create_response.status_code, 400)

    @patch("apps.bookings.services.reminder_service.send_telegram_message", return_value=True)
    def test_send_reminders_skips_cancelled_bookings_and_marks_sent_once(self, _send_message) -> None:
        from django.core.management import call_command

        active = Booking.objects.create(
            organization=self.org,
            branch=self.branch,
            client=self.client_user,
            car=self.car,
            service=self.service,
            workstation=self.ws1,
            start_at=timezone.now() + timedelta(hours=2),
            end_at=timezone.now() + timedelta(hours=3),
            price=self.service.price,
            status=BookingStatus.PENDING,
        )
        cancelled = Booking.objects.create(
            organization=self.org,
            branch=self.branch,
            client=self.other_client,
            car=self.other_car,
            service=self.service,
            workstation=self.ws2,
            start_at=timezone.now() + timedelta(hours=2),
            end_at=timezone.now() + timedelta(hours=3),
            price=self.service.price,
            status=BookingStatus.CANCELLED,
        )
        active_reminder = BookingReminder.objects.create(
            booking=active,
            kind=BookingReminderKind.HOUR_BEFORE,
            scheduled_at=timezone.now() - timedelta(minutes=1),
        )
        BookingReminder.objects.create(
            booking=cancelled,
            kind=BookingReminderKind.HOUR_BEFORE,
            scheduled_at=timezone.now() - timedelta(minutes=1),
        )

        call_command("send_booking_reminders")
        active_reminder.refresh_from_db()
        self.assertIsNotNone(active_reminder.sent_at)
        self.assertEqual(active_reminder.status, BookingReminderStatus.SENT)
        self.assertEqual(active_reminder.attempts, 1)
        self.assertIsNotNone(active_reminder.last_attempt_at)
        self.assertEqual(BookingReminder.objects.filter(sent_at__isnull=False).count(), 1)

        call_command("send_booking_reminders")
        self.assertEqual(BookingReminder.objects.filter(sent_at__isnull=False).count(), 1)

    def test_celery_tasks_are_registered(self) -> None:
        from config.celery import app

        app.loader.import_default_modules()
        self.assertIn("apps.bookings.tasks.process_due_booking_reminders", app.tasks)
        self.assertIn("apps.bookings.tasks.send_booking_reminder", app.tasks)
        self.assertIn("apps.bookings.tasks.process_overdue_bookings", app.tasks)

    def test_celery_beat_registers_booking_lifecycle_scan(self) -> None:
        from django.conf import settings

        self.assertEqual(
            settings.CELERY_BEAT_SCHEDULE["process-overdue-bookings"]["task"],
            "apps.bookings.tasks.process_overdue_bookings",
        )

    def make_direct_booking(self, *, status: str, start_at: datetime, end_at: datetime) -> Booking:
        return Booking.objects.create(
            organization=self.org,
            branch=self.branch,
            client=self.client_user,
            car=self.car,
            service=self.service,
            workstation=self.ws1,
            start_at=start_at,
            end_at=end_at,
            price=self.service.price,
            status=status,
        )

    def test_pending_future_booking_is_not_auto_changed(self) -> None:
        from apps.bookings.services.lifecycle_service import process_overdue_bookings

        now = timezone.now()
        booking = self.make_direct_booking(
            status=BookingStatus.PENDING,
            start_at=now + timedelta(minutes=30),
            end_at=now + timedelta(minutes=90),
        )

        self.assertEqual(process_overdue_bookings(now=now), 0)
        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.PENDING)

    def test_pending_overdue_booking_is_marked_no_show(self) -> None:
        from apps.bookings.services.lifecycle_service import process_overdue_bookings

        now = timezone.now()
        booking = self.make_direct_booking(
            status=BookingStatus.PENDING,
            start_at=now - timedelta(hours=2),
            end_at=now - timedelta(minutes=1),
        )
        reminder = BookingReminder.objects.create(
            booking=booking,
            kind=BookingReminderKind.HOUR_BEFORE,
            scheduled_at=now - timedelta(hours=3),
        )

        self.assertEqual(process_overdue_bookings(now=now), 1)
        booking.refresh_from_db()
        reminder.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.NO_SHOW)
        self.assertEqual(reminder.status, BookingReminderStatus.CANCELLED)

    def test_confirmed_booking_during_service_window_is_not_auto_completed(self) -> None:
        from apps.bookings.services.lifecycle_service import process_overdue_bookings

        now = timezone.now()
        booking = self.make_direct_booking(
            status=BookingStatus.CONFIRMED,
            start_at=now - timedelta(minutes=15),
            end_at=now + timedelta(minutes=45),
        )

        self.assertEqual(process_overdue_bookings(now=now), 0)
        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.CONFIRMED)

    def test_confirmed_overdue_booking_without_arrival_is_marked_no_show(self) -> None:
        from apps.bookings.services.lifecycle_service import process_overdue_bookings

        now = timezone.now()
        booking = self.make_direct_booking(
            status=BookingStatus.CONFIRMED,
            start_at=now - timedelta(hours=2),
            end_at=now - timedelta(minutes=1),
        )

        self.assertEqual(process_overdue_bookings(now=now), 1)
        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.NO_SHOW)

    def test_arrived_in_progress_and_ready_are_not_auto_no_show(self) -> None:
        from apps.bookings.services.lifecycle_service import process_overdue_bookings

        now = timezone.now()
        bookings = [
            self.make_direct_booking(status=status, start_at=now - timedelta(hours=2), end_at=now - timedelta(minutes=1))
            for status in (BookingStatus.ARRIVED, BookingStatus.IN_PROGRESS, BookingStatus.READY)
        ]

        self.assertEqual(process_overdue_bookings(now=now), 0)
        self.assertEqual(
            list(Booking.objects.filter(id__in=[booking.id for booking in bookings]).order_by("status").values_list("status", flat=True)),
            sorted([BookingStatus.ARRIVED, BookingStatus.IN_PROGRESS, BookingStatus.READY]),
        )

    def test_final_booking_statuses_are_not_auto_changed(self) -> None:
        from apps.bookings.services.lifecycle_service import process_overdue_bookings

        now = timezone.now()
        bookings = [
            self.make_direct_booking(status=status, start_at=now - timedelta(hours=2), end_at=now - timedelta(minutes=1))
            for status in (BookingStatus.CANCELLED, BookingStatus.COMPLETED, BookingStatus.NO_SHOW)
        ]

        self.assertEqual(process_overdue_bookings(now=now), 0)
        self.assertEqual(
            list(Booking.objects.filter(id__in=[booking.id for booking in bookings]).order_by("status").values_list("status", flat=True)),
            sorted([BookingStatus.CANCELLED, BookingStatus.COMPLETED, BookingStatus.NO_SHOW]),
        )

    def test_booking_changed_by_admin_before_lifecycle_update_is_preserved(self) -> None:
        from apps.bookings.services.lifecycle_service import get_overdue_booking_ids, mark_booking_no_show_if_overdue

        now = timezone.now()
        booking = self.make_direct_booking(
            status=BookingStatus.CONFIRMED,
            start_at=now - timedelta(hours=2),
            end_at=now - timedelta(minutes=1),
        )

        self.assertIn(booking.id, get_overdue_booking_ids(now=now))
        booking.status = BookingStatus.ARRIVED
        booking.save(update_fields=["status", "updated_at"])

        self.assertFalse(mark_booking_no_show_if_overdue(booking.id, now=now))
        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.ARRIVED)

    def test_lifecycle_scan_is_idempotent(self) -> None:
        from apps.bookings.services.lifecycle_service import process_overdue_bookings

        now = timezone.now()
        booking = self.make_direct_booking(
            status=BookingStatus.PENDING,
            start_at=now - timedelta(hours=2),
            end_at=now - timedelta(minutes=1),
        )

        self.assertEqual(process_overdue_bookings(now=now), 1)
        self.assertEqual(process_overdue_bookings(now=now), 0)
        booking.refresh_from_db()
        self.assertEqual(booking.status, BookingStatus.NO_SHOW)

    def test_lifecycle_time_boundaries_use_end_at_strictly(self) -> None:
        from apps.bookings.services.lifecycle_service import process_overdue_bookings

        now = timezone.now()
        starts_at_now = self.make_direct_booking(
            status=BookingStatus.PENDING,
            start_at=now,
            end_at=now + timedelta(hours=1),
        )
        ends_at_now = self.make_direct_booking(
            status=BookingStatus.PENDING,
            start_at=now - timedelta(hours=1),
            end_at=now,
        )
        just_after_end = self.make_direct_booking(
            status=BookingStatus.PENDING,
            start_at=now - timedelta(hours=1),
            end_at=now - timedelta(microseconds=1),
        )

        self.assertEqual(process_overdue_bookings(now=now), 1)
        starts_at_now.refresh_from_db()
        ends_at_now.refresh_from_db()
        just_after_end.refresh_from_db()
        self.assertEqual(starts_at_now.status, BookingStatus.PENDING)
        self.assertEqual(ends_at_now.status, BookingStatus.PENDING)
        self.assertEqual(just_after_end.status, BookingStatus.NO_SHOW)

    def test_client_api_returns_lifecycle_updated_status(self) -> None:
        from apps.bookings.services.lifecycle_service import process_overdue_bookings

        now = timezone.now()
        booking = self.make_direct_booking(
            status=BookingStatus.PENDING,
            start_at=now - timedelta(hours=2),
            end_at=now - timedelta(minutes=1),
        )

        process_overdue_bookings(now=now)
        response = self.auth_client(self.client_user).get(f"/api/my-bookings/{booking.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], BookingStatus.NO_SHOW)

    def test_reminder_service_sends_correct_booking_and_keeps_tenant_context(self) -> None:
        from apps.bookings.services.reminder_service import process_due_booking_reminders

        own_booking = Booking.objects.create(
            organization=self.org,
            branch=self.branch,
            client=self.client_user,
            car=self.car,
            service=self.service,
            workstation=self.ws1,
            start_at=timezone.now() + timedelta(hours=2),
            end_at=timezone.now() + timedelta(hours=3),
            price=self.service.price,
            status=BookingStatus.PENDING,
        )
        other_booking = Booking.objects.create(
            organization=self.other_org,
            branch=self.other_branch,
            client=self.other_admin,
            car=Car.objects.create(owner=self.other_admin, brand="Kia", model="Rio", license_plate="O111OO", color="Red"),
            service=self.other_service,
            workstation=self.other_ws,
            start_at=timezone.now() + timedelta(hours=2),
            end_at=timezone.now() + timedelta(hours=3),
            price=self.other_service.price,
            status=BookingStatus.PENDING,
        )
        BookingReminder.objects.create(booking=own_booking, kind=BookingReminderKind.HOUR_BEFORE, scheduled_at=timezone.now() - timedelta(minutes=1))
        BookingReminder.objects.create(booking=other_booking, kind=BookingReminderKind.HOUR_BEFORE, scheduled_at=timezone.now() - timedelta(minutes=1))
        calls: list[tuple[int | None, str]] = []

        sent = process_due_booking_reminders(sender=lambda telegram_id, text: calls.append((telegram_id, text)) or True)

        self.assertEqual(sent, 2)
        self.assertEqual({call[0] for call in calls}, {self.client_user.telegram_id, self.other_admin.telegram_id})
        self.assertTrue(any("Услуга: Wash" in call[1] for call in calls))
        self.assertTrue(any("Услуга: Other" in call[1] for call in calls))

    def test_admin_notification_history_is_tenant_scoped(self) -> None:
        own_booking = Booking.objects.create(
            organization=self.org,
            branch=self.branch,
            client=self.client_user,
            car=self.car,
            service=self.service,
            workstation=self.ws1,
            start_at=timezone.now() + timedelta(hours=2),
            end_at=timezone.now() + timedelta(hours=3),
            price=self.service.price,
            status=BookingStatus.PENDING,
        )
        other_booking = Booking.objects.create(
            organization=self.other_org,
            branch=self.other_branch,
            client=self.other_admin,
            car=Car.objects.create(owner=self.other_admin, brand="Kia", model="Rio", license_plate="O111OO", color="Red"),
            service=self.other_service,
            workstation=self.other_ws,
            start_at=timezone.now() + timedelta(hours=2),
            end_at=timezone.now() + timedelta(hours=3),
            price=self.other_service.price,
            status=BookingStatus.PENDING,
        )
        own_reminder = BookingReminder.objects.create(booking=own_booking, kind=BookingReminderKind.HOUR_BEFORE, scheduled_at=timezone.now())
        other_reminder = BookingReminder.objects.create(booking=other_booking, kind=BookingReminderKind.HOUR_BEFORE, scheduled_at=timezone.now())

        response = self.auth_client(self.admin).get("/api/admin/notifications/")

        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in response.data["results"]}
        self.assertIn(str(own_reminder.id), ids)
        self.assertNotIn(str(other_reminder.id), ids)

    def test_reminder_service_skips_wrong_timing(self) -> None:
        from apps.bookings.services.reminder_service import process_due_booking_reminders

        future_booking = Booking.objects.create(
            organization=self.org,
            branch=self.branch,
            client=self.client_user,
            car=self.car,
            service=self.service,
            workstation=self.ws1,
            start_at=timezone.now() + timedelta(hours=2),
            end_at=timezone.now() + timedelta(hours=3),
            price=self.service.price,
            status=BookingStatus.PENDING,
        )
        past_booking = Booking.objects.create(
            organization=self.org,
            branch=self.branch,
            client=self.other_client,
            car=self.other_car,
            service=self.service,
            workstation=self.ws2,
            start_at=timezone.now() - timedelta(minutes=5),
            end_at=timezone.now() + timedelta(minutes=55),
            price=self.service.price,
            status=BookingStatus.PENDING,
        )
        BookingReminder.objects.create(booking=future_booking, kind=BookingReminderKind.HOUR_BEFORE, scheduled_at=timezone.now() + timedelta(minutes=30))
        BookingReminder.objects.create(booking=past_booking, kind=BookingReminderKind.HOUR_BEFORE, scheduled_at=timezone.now() - timedelta(minutes=30))

        sent = process_due_booking_reminders(sender=lambda _telegram_id, _text: True)

        self.assertEqual(sent, 0)
        self.assertEqual(BookingReminder.objects.filter(sent_at__isnull=False).count(), 0)

    def test_reminder_service_does_not_mark_sent_when_delivery_fails(self) -> None:
        from apps.bookings.services.reminder_service import ReminderDeliveryError, process_due_booking_reminders

        booking = Booking.objects.create(
            organization=self.org,
            branch=self.branch,
            client=self.client_user,
            car=self.car,
            service=self.service,
            workstation=self.ws1,
            start_at=timezone.now() + timedelta(hours=2),
            end_at=timezone.now() + timedelta(hours=3),
            price=self.service.price,
            status=BookingStatus.PENDING,
        )
        reminder = BookingReminder.objects.create(booking=booking, kind=BookingReminderKind.HOUR_BEFORE, scheduled_at=timezone.now() - timedelta(minutes=1))

        with self.assertRaises(ReminderDeliveryError):
            process_due_booking_reminders(sender=lambda _telegram_id, _text: False)

        reminder.refresh_from_db()
        self.assertIsNone(reminder.sent_at)
        self.assertEqual(reminder.status, BookingReminderStatus.PENDING)
        self.assertEqual(reminder.attempts, 1)
        self.assertIsNotNone(reminder.last_attempt_at)
        self.assertIn("unsuccessful", reminder.error_message)

    def test_due_reminder_scan_recovers_stale_pending_attempts(self) -> None:
        from apps.bookings.services.reminder_service import get_due_booking_reminder_ids

        booking = Booking.objects.create(
            organization=self.org,
            branch=self.branch,
            client=self.client_user,
            car=self.car,
            service=self.service,
            workstation=self.ws1,
            start_at=timezone.now() + timedelta(hours=2),
            end_at=timezone.now() + timedelta(hours=3),
            price=self.service.price,
            status=BookingStatus.PENDING,
        )
        stale = BookingReminder.objects.create(
            booking=booking,
            kind=BookingReminderKind.HOUR_BEFORE,
            scheduled_at=timezone.now() - timedelta(minutes=10),
            attempts=1,
            last_attempt_at=timezone.now() - timedelta(minutes=10),
        )
        recent = BookingReminder.objects.create(
            booking=booking,
            kind=BookingReminderKind.DAY_BEFORE,
            scheduled_at=timezone.now() - timedelta(minutes=10),
            attempts=1,
            last_attempt_at=timezone.now(),
        )

        due_ids = set(get_due_booking_reminder_ids())

        self.assertIn(stale.id, due_ids)
        self.assertNotIn(recent.id, due_ids)

    @patch("apps.bookings.tasks.send_booking_reminder_task")
    def test_process_due_reminders_task_enqueues_due_reminders(self, send_reminder_task) -> None:
        from apps.bookings.tasks import process_due_booking_reminders

        booking = Booking.objects.create(
            organization=self.org,
            branch=self.branch,
            client=self.client_user,
            car=self.car,
            service=self.service,
            workstation=self.ws1,
            start_at=timezone.now() + timedelta(hours=2),
            end_at=timezone.now() + timedelta(hours=3),
            price=self.service.price,
            status=BookingStatus.PENDING,
        )
        reminder = BookingReminder.objects.create(booking=booking, kind=BookingReminderKind.HOUR_BEFORE, scheduled_at=timezone.now() - timedelta(minutes=1))

        due_count = process_due_booking_reminders()

        self.assertEqual(due_count, 1)
        send_reminder_task.delay.assert_called_once_with(str(reminder.id))

    @patch("apps.bookings.tasks.send_booking_reminder")
    def test_send_reminder_task_retries_temporary_delivery_error(self, send_reminder) -> None:
        from celery.exceptions import Retry
        from unittest.mock import patch as mock_patch

        from apps.bookings.services.reminder_service import ReminderDeliveryError
        from apps.bookings.tasks import send_booking_reminder_task

        send_reminder.side_effect = ReminderDeliveryError("temporary")
        send_booking_reminder_task.request.retries = 0

        with mock_patch.object(send_booking_reminder_task, "retry", side_effect=Retry()) as retry:
            with self.assertRaises(Retry):
                send_booking_reminder_task.run("00000000-0000-0000-0000-000000000000")
        retry.assert_called_once()

    @patch("apps.bookings.tasks.send_booking_reminder")
    def test_send_reminder_task_marks_failed_after_retry_limit(self, send_reminder) -> None:
        from apps.bookings.services.reminder_service import ReminderDeliveryError
        from apps.bookings.tasks import send_booking_reminder_task

        booking = Booking.objects.create(
            organization=self.org,
            branch=self.branch,
            client=self.client_user,
            car=self.car,
            service=self.service,
            workstation=self.ws1,
            start_at=timezone.now() + timedelta(hours=2),
            end_at=timezone.now() + timedelta(hours=3),
            price=self.service.price,
            status=BookingStatus.PENDING,
        )
        reminder = BookingReminder.objects.create(booking=booking, kind=BookingReminderKind.HOUR_BEFORE, scheduled_at=timezone.now() - timedelta(minutes=1))
        send_reminder.side_effect = ReminderDeliveryError("temporary")

        send_booking_reminder_task.request.retries = 3
        result = send_booking_reminder_task.run(str(reminder.id))

        self.assertFalse(result)
        reminder.refresh_from_db()
        self.assertEqual(reminder.status, BookingReminderStatus.FAILED)
        self.assertEqual(reminder.error_message, "temporary")

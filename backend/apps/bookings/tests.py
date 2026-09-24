from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.branches.models import Branch
from apps.cars.models import Car
from apps.organizations.models import Organization
from apps.schedules.models import BusinessHour, ScheduleException
from apps.services.models import Service
from apps.workstations.models import Workstation

from .models import Booking, BookingStatus


class BookingEngineTests(TestCase):
    def setUp(self) -> None:
        self.org = Organization.objects.create(name="Clean Auto", slug="clean-auto")
        self.other_org = Organization.objects.create(name="Other Auto", slug="other-auto")
        self.branch = Branch.objects.create(organization=self.org, name="Center", address="Main", timezone="Asia/Almaty")
        self.other_branch = Branch.objects.create(organization=self.other_org, name="Other", address="Other", timezone="Asia/Almaty")
        BusinessHour.objects.create(branch=self.branch, weekday=3, opening_time=time(9), closing_time=time(21))
        BusinessHour.objects.create(branch=self.other_branch, weekday=3, opening_time=time(9), closing_time=time(21))
        self.ws1 = Workstation.objects.create(branch=self.branch, name="Box 1")
        self.ws2 = Workstation.objects.create(branch=self.branch, name="Box 2")
        self.other_ws = Workstation.objects.create(branch=self.other_branch, name="Other Box")
        self.client_user = User.objects.create_user(username="client", telegram_id=4001, role=UserRole.CLIENT, organization=self.org)
        self.other_client = User.objects.create_user(username="other-client", telegram_id=4002, role=UserRole.CLIENT, organization=self.org)
        self.admin = User.objects.create_user(username="admin", telegram_id=4003, role=UserRole.ADMIN, organization=self.org)
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
        return datetime(2026, 10, 1, hour, minute, tzinfo=ZoneInfo("Asia/Almaty")).isoformat()

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
        ScheduleException.objects.create(branch=self.branch, date=date(2026, 10, 1), is_closed=True)
        self.assertEqual(self.create_booking(start_at=self.local_dt(10)).status_code, 400)

    def test_schedule_exception_has_priority_for_booking(self) -> None:
        ScheduleException.objects.create(
            branch=self.branch,
            date=date(2026, 10, 1),
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
            f"/api/branches/{self.branch.id}/availability/?date=2026-10-01&service_id={self.long_service.id}"
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
            start_at=datetime(2026, 10, 1, 13, tzinfo=ZoneInfo("Asia/Almaty")),
            end_at=datetime(2026, 10, 1, 14, tzinfo=ZoneInfo("Asia/Almaty")),
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
            start_at=datetime(2026, 10, 1, 13, tzinfo=ZoneInfo("Asia/Almaty")),
            end_at=datetime(2026, 10, 1, 14, tzinfo=ZoneInfo("Asia/Almaty")),
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
            start_at=datetime(2026, 10, 1, 13, tzinfo=ZoneInfo("Asia/Almaty")),
            end_at=datetime(2026, 10, 1, 14, tzinfo=ZoneInfo("Asia/Almaty")),
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

    def test_repeat_creation_is_protected_when_all_workstations_blocked(self) -> None:
        self.assertEqual(self.create_booking().status_code, 201)
        self.assertEqual(self.create_booking().status_code, 201)
        response = self.create_booking()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            Booking.objects.filter(workstation=self.ws1, status__in=[BookingStatus.PENDING]).count(),
            1,
        )

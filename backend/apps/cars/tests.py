from datetime import date, time

from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.branches.models import Branch
from apps.cars.models import Car
from apps.organizations.models import Organization
from apps.schedules.models import BusinessHour, ScheduleException
from apps.schedules.services import get_branch_schedule
from apps.services.models import Service
from apps.workstations.models import Workstation


class DomainApiTests(TestCase):
    def setUp(self) -> None:
        self.org = Organization.objects.create(name="Clean Auto", slug="clean-auto")
        self.other_org = Organization.objects.create(name="Other Auto", slug="other-auto")
        self.branch = Branch.objects.create(organization=self.org, name="Center", address="Main")
        self.other_branch = Branch.objects.create(organization=self.other_org, name="Other", address="Other")
        self.client_user = User.objects.create_user(
            username="client",
            telegram_id=3001,
            role=UserRole.CLIENT,
            organization=self.org,
        )
        self.other_client = User.objects.create_user(
            username="other-client",
            telegram_id=3002,
            role=UserRole.CLIENT,
            organization=self.org,
        )
        self.admin = User.objects.create_user(
            username="admin",
            telegram_id=3003,
            role=UserRole.ADMIN,
            organization=self.org,
        )
        self.other_admin = User.objects.create_user(
            username="other-admin",
            telegram_id=3004,
            role=UserRole.ADMIN,
            organization=self.other_org,
        )
        self.owner = User.objects.create_user(
            username="owner",
            telegram_id=3005,
            role=UserRole.OWNER,
            organization=self.org,
        )

    def auth_client(self, user: User) -> APIClient:
        token, _ = Token.objects.get_or_create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return client

    def test_client_can_create_car(self) -> None:
        response = self.auth_client(self.client_user).post(
            "/api/my-cars/",
            {"brand": "Toyota", "model": "Camry", "license_plate": " a123bc ", "color": "Белый"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["license_plate"], "A123BC")
        self.assertEqual(Car.objects.get().owner, self.client_user)

    def test_client_can_get_own_car(self) -> None:
        car = Car.objects.create(owner=self.client_user, brand="Toyota", model="Camry", license_plate="A123BC", color="Белый")

        response = self.auth_client(self.client_user).get(f"/api/my-cars/{car.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(car.id))

    def test_client_cannot_get_other_client_car(self) -> None:
        car = Car.objects.create(owner=self.other_client, brand="BMW", model="X5", license_plate="B777BB", color="Черный")

        response = self.auth_client(self.client_user).get(f"/api/my-cars/{car.id}/")

        self.assertEqual(response.status_code, 404)

    def test_client_cannot_update_other_client_car(self) -> None:
        car = Car.objects.create(owner=self.other_client, brand="BMW", model="X5", license_plate="B777BB", color="Черный")

        response = self.auth_client(self.client_user).patch(f"/api/my-cars/{car.id}/", {"color": "Серый"}, format="json")

        self.assertEqual(response.status_code, 404)
        car.refresh_from_db()
        self.assertEqual(car.color, "Черный")

    def test_client_cannot_delete_other_client_car(self) -> None:
        car = Car.objects.create(owner=self.other_client, brand="BMW", model="X5", license_plate="B777BB", color="Черный")

        response = self.auth_client(self.client_user).delete(f"/api/my-cars/{car.id}/")

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Car.objects.filter(id=car.id).exists())

    def test_client_cannot_create_duplicate_license_plate(self) -> None:
        Car.objects.create(owner=self.client_user, brand="Toyota", model="Camry", license_plate="A123BC", color="Белый")

        response = self.auth_client(self.client_user).post(
            "/api/my-cars/",
            {"brand": "Toyota", "model": "RAV4", "license_plate": " a123bc ", "color": "Серый"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_client_sees_only_active_services_for_own_organization(self) -> None:
        active = Service.objects.create(organization=self.org, name="Кузов", duration_minutes=30, price="700.00")
        Service.objects.create(organization=self.org, name="Архивная", duration_minutes=30, price="500.00", is_active=False)
        Service.objects.create(organization=self.other_org, name="Чужая", duration_minutes=30, price="900.00")

        response = self.auth_client(self.client_user).get("/api/services/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [str(active.id)])

    def test_admin_sees_services_for_own_organization_only(self) -> None:
        own = Service.objects.create(organization=self.org, name="Салон", duration_minutes=45, price="1000.00")
        Service.objects.create(organization=self.other_org, name="Чужая", duration_minutes=30, price="900.00")

        response = self.auth_client(self.admin).get("/api/admin/services/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [str(own.id)])

    def test_owner_has_access_to_own_organization_services(self) -> None:
        response = self.auth_client(self.owner).post(
            "/api/admin/services/",
            {"name": "Воск", "duration_minutes": 20, "price": "400.00", "is_active": True},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Service.objects.get(id=response.data["id"]).organization, self.org)

    def test_admin_can_manage_workstation_for_own_organization(self) -> None:
        response = self.auth_client(self.admin).post(
            "/api/admin/workstations/",
            {"branch": str(self.branch.id), "name": "Box 1", "is_active": True},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Workstation.objects.get(id=response.data["id"]).branch, self.branch)

    def test_admin_cannot_get_workstation_from_other_organization(self) -> None:
        workstation = Workstation.objects.create(branch=self.other_branch, name="Box X")

        response = self.auth_client(self.admin).get(f"/api/admin/workstations/{workstation.id}/")

        self.assertEqual(response.status_code, 404)

    def test_business_hour_returns_schedule(self) -> None:
        BusinessHour.objects.create(
            branch=self.branch,
            weekday=0,
            opening_time=time(9, 0),
            closing_time=time(21, 0),
        )

        schedule = get_branch_schedule(self.branch, date(2027, 1, 4))

        self.assertFalse(schedule.is_closed)
        self.assertEqual(schedule.opening_time, time(9, 0))
        self.assertEqual(schedule.closing_time, time(21, 0))
        self.assertEqual(schedule.source, "business_hour")

    def test_schedule_exception_has_priority(self) -> None:
        BusinessHour.objects.create(
            branch=self.branch,
            weekday=3,
            opening_time=time(9, 0),
            closing_time=time(21, 0),
        )
        ScheduleException.objects.create(
            branch=self.branch,
            date=date(2026, 12, 31),
            opening_time=time(10, 0),
            closing_time=time(17, 0),
            reason="Сокращенный день",
        )

        schedule = get_branch_schedule(self.branch, date(2026, 12, 31))

        self.assertFalse(schedule.is_closed)
        self.assertEqual(schedule.opening_time, time(10, 0))
        self.assertEqual(schedule.closing_time, time(17, 0))
        self.assertEqual(schedule.source, "exception")

    def test_closed_day_returns_closed(self) -> None:
        ScheduleException.objects.create(
            branch=self.branch,
            date=date(2027, 1, 1),
            is_closed=True,
            reason="Праздник",
        )

        schedule = get_branch_schedule(self.branch, date(2027, 1, 1))

        self.assertTrue(schedule.is_closed)
        self.assertIsNone(schedule.opening_time)
        self.assertIsNone(schedule.closing_time)

    def test_client_branch_schedule_rejects_invalid_date(self) -> None:
        response = self.auth_client(self.client_user).get(f"/api/branches/{self.branch.id}/schedule/?date=not-a-date")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "INVALID_DATE")

from __future__ import annotations

from datetime import time
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.branches.models import Branch
from apps.organizations.models import Organization
from apps.schedules.models import BusinessHour
from apps.services.models import Service
from apps.workstations.models import Workstation


class Command(BaseCommand):
    help = "Create demo organization, branch, services, workstations, and schedule for local development."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--slug", default="clean-auto", help="Organization slug used by Telegram start flow.")
        parser.add_argument("--timezone", default="Asia/Almaty", help="IANA timezone for the demo branch.")

    def handle(self, *args, **options) -> None:
        slug = options["slug"]
        branch_timezone = options["timezone"]

        organization, org_created = Organization.objects.update_or_create(
            slug=slug,
            defaults={
                "name": "Clean Auto",
                "description": "Демо-автомойка MultiAuto для локального запуска.",
                "phone": "+7 700 000 00 00",
                "email": "demo@multiauto.local",
                "address": "Демо-адрес, 1",
                "is_active": True,
            },
        )

        branch, branch_created = Branch.objects.update_or_create(
            organization=organization,
            name="Центральный филиал",
            defaults={
                "address": "Демо-адрес, 1",
                "phone": "+7 700 000 00 01",
                "timezone": branch_timezone,
                "is_active": True,
            },
        )

        services = [
            ("Кузов", "Наружная мойка кузова.", 30, Decimal("700.00")),
            ("Салон", "Влажная уборка и чистка салона.", 45, Decimal("1000.00")),
            ("Комплексная мойка", "Кузов, салон, коврики и базовая сушка.", 60, Decimal("1500.00")),
            ("Воск", "Защитное покрытие воском после мойки.", 30, Decimal("800.00")),
            ("Химчистка", "Глубокая чистка салона.", 120, Decimal("4500.00")),
        ]
        created_services = 0
        for name, description, duration, price in services:
            _, created = Service.objects.update_or_create(
                organization=organization,
                name=name,
                defaults={
                    "description": description,
                    "duration_minutes": duration,
                    "price": price,
                    "is_active": True,
                },
            )
            created_services += int(created)

        created_workstations = 0
        for name in ("Box 1", "Box 2", "Box 3"):
            _, created = Workstation.objects.update_or_create(
                branch=branch,
                name=name,
                defaults={"is_active": True},
            )
            created_workstations += int(created)

        created_hours = 0
        for weekday in range(7):
            is_closed = weekday == 6
            defaults = {
                "is_closed": is_closed,
                "opening_time": None if is_closed else time(9, 0),
                "closing_time": None if is_closed else time(21, 0),
            }
            _, created = BusinessHour.objects.update_or_create(
                branch=branch,
                weekday=weekday,
                defaults=defaults,
            )
            created_hours += int(created)

        self.stdout.write(self.style.SUCCESS("Demo data is ready."))
        self.stdout.write(f"Organization: {organization.name} ({organization.slug}) {'created' if org_created else 'updated'}")
        self.stdout.write(f"Branch: {branch.name} {'created' if branch_created else 'updated'}")
        self.stdout.write(f"Services created: {created_services}")
        self.stdout.write(f"Workstations created: {created_workstations}")
        self.stdout.write(f"Business hours created: {created_hours}")
        self.stdout.write("Use TELEGRAM_DEFAULT_ORGANIZATION_SLUG=clean-auto for /start without deep link.")

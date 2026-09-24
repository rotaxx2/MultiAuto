from django.db import IntegrityError
from django.test import TestCase

from apps.organizations.models import Organization


class OrganizationModelTests(TestCase):
    def test_slug_is_unique(self) -> None:
        Organization.objects.create(name="Clean Auto", slug="clean-auto")

        with self.assertRaises(IntegrityError):
            Organization.objects.create(name="Another Auto", slug="clean-auto")

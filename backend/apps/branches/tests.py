from django.db import IntegrityError
from django.test import TestCase

from apps.branches.models import Branch
from apps.organizations.models import Organization


class BranchModelTests(TestCase):
    def test_branch_name_is_unique_inside_organization(self) -> None:
        organization = Organization.objects.create(name="Clean Auto", slug="clean-auto")
        Branch.objects.create(organization=organization, name="Center", address="A")

        with self.assertRaises(IntegrityError):
            Branch.objects.create(organization=organization, name="Center", address="B")

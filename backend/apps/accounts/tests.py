from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models import User, UserRole
from apps.accounts.permissions import belongs_to_user_organization, for_user_organization
from apps.branches.models import Branch
from apps.organizations.models import Organization


class FoundationModelTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(
            name="Clean Auto",
            slug="clean-auto",
            phone="+79990000000",
            email="owner@example.com",
            address="Main street, 1",
        )

    def test_create_user(self) -> None:
        user = User.objects.create_user(
            username="client-1",
            password="safe-test-password",
            telegram_id=123456789,
            first_name="Ivan",
            role=UserRole.CLIENT,
            organization=self.organization,
        )

        self.assertEqual(user.telegram_id, 123456789)
        self.assertEqual(user.role, UserRole.CLIENT)
        self.assertEqual(user.organization, self.organization)

    def test_telegram_id_is_unique(self) -> None:
        User.objects.create_user(username="client-1", telegram_id=777, organization=self.organization)

        with self.assertRaises(IntegrityError):
            User.objects.create_user(username="client-2", telegram_id=777, organization=self.organization)

    def test_roles_are_limited_to_documented_values(self) -> None:
        self.assertEqual({choice[0] for choice in UserRole.choices}, {"CLIENT", "ADMIN", "OWNER"})

        user = User(username="invalid-role", role="WORKER", organization=self.organization)
        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_create_organization(self) -> None:
        self.assertEqual(self.organization.slug, "clean-auto")
        self.assertTrue(self.organization.is_active)

    def test_create_branch(self) -> None:
        branch = Branch.objects.create(
            organization=self.organization,
            name="Branch 1",
            address="Branch street, 10",
        )

        self.assertEqual(branch.organization, self.organization)
        self.assertTrue(branch.is_active)

    def test_user_organization_relation(self) -> None:
        owner = User.objects.create_user(
            username="owner",
            telegram_id=900,
            role=UserRole.OWNER,
            organization=self.organization,
        )

        self.assertEqual(owner.organization, self.organization)
        self.assertEqual(self.organization.users.get(id=owner.id), owner)

    def test_basic_tenant_filtering(self) -> None:
        other_org = Organization.objects.create(name="Other Auto", slug="other-auto")
        admin = User.objects.create_user(
            username="admin",
            telegram_id=901,
            role=UserRole.ADMIN,
            organization=self.organization,
        )
        own_branch = Branch.objects.create(
            organization=self.organization,
            name="Own branch",
            address="Own address",
        )
        Branch.objects.create(
            organization=other_org,
            name="Other branch",
            address="Other address",
        )

        scoped = for_user_organization(Branch.objects.all(), admin)

        self.assertEqual(list(scoped), [own_branch])
        self.assertTrue(belongs_to_user_organization(admin, own_branch))

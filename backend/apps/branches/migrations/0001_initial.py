# Generated for MultiAuto Backend Foundation.

import django.db.models.deletion
import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Branch",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("address", models.TextField()),
                ("phone", models.CharField(blank=True, max_length=32)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="branches",
                        to="organizations.organization",
                    ),
                ),
            ],
            options={
                "ordering": ["organization__name", "name"],
            },
        ),
        migrations.AddConstraint(
            model_name="branch",
            constraint=models.UniqueConstraint(fields=("organization", "name"), name="branches_org_name_uq"),
        ),
        migrations.AddIndex(
            model_name="branch",
            index=models.Index(fields=["organization"], name="branches_org_idx"),
        ),
        migrations.AddIndex(
            model_name="branch",
            index=models.Index(fields=["organization", "is_active"], name="branches_org_active_idx"),
        ),
    ]

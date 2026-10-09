# Infinity Planning has no cycles, modules, estimates or Guest role.

from django.db import migrations, models

GUEST_ROLE = 5
MEMBER_ROLE = 15
MEMBER_MODELS = ["WorkspaceMember", "WorkspaceMemberInvite", "ProjectMember", "ProjectMemberInvite"]


def disable_features(apps, schema_editor):
    # _base_manager also reaches soft-deleted rows, so a restored row stays consistent.
    Project = apps.get_model("db", "Project")
    Project._base_manager.update(cycle_view=False, module_view=False, estimate=None)

    for model_name in MEMBER_MODELS:
        model = apps.get_model("db", model_name)
        model._base_manager.filter(role=GUEST_ROLE).update(role=MEMBER_ROLE)


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0122_alter_draftissue_assignees_alter_issue_assignees_and_more"),
    ]

    operations = [
        migrations.RunPython(disable_features, migrations.RunPython.noop),
    ] + [
        migrations.AlterField(
            model_name=model_name.lower(),
            name="role",
            field=models.PositiveSmallIntegerField(
                choices=[(20, "Admin"), (15, "Member"), (5, "Guest")], default=MEMBER_ROLE
            ),
        )
        for model_name in MEMBER_MODELS
    ]

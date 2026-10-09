# Infinity Planning is used in French: French becomes the default language, and the
# profiles still on the former English default switch to French.

from django.db import migrations, models


def switch_english_profiles_to_french(apps, schema_editor):
    Profile = apps.get_model("db", "Profile")
    Profile._base_manager.filter(language="en").update(language="fr")


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0123_infinity_disable_cycles_modules_estimates_guest"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="language",
            field=models.CharField(default="fr", max_length=255),
        ),
        migrations.RunPython(switch_english_profiles_to_french, migrations.RunPython.noop),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0125_infinity_custom_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="apitoken",
            name="client",
            field=models.CharField(blank=True, choices=[("claude", "Claude")], default="", max_length=50),
        ),
        migrations.AddField(
            model_name="issueactivity",
            name="via",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
    ]

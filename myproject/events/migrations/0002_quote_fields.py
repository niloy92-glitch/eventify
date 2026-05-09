from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventservicebooking",
            name="quoted_price",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="eventservicebooking",
            name="quote_note",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="eventservicebooking",
            name="quoted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="eventservicebooking",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("quoted", "Quoted"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
# Generated by Django 4.2.9 on 2024-02-05 13:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_availableslot'),
    ]

    operations = [
        migrations.CreateModel(
            name='TimeAvailability',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('available_slot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='app.availableslot')),
            ],
        ),
    ]
# Generated by Django 5.1.7 on 2025-04-01 14:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crudapp', '0002_employee_email'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='PhoneNumber',
            field=models.CharField(default='', max_length=15),
        ),
    ]

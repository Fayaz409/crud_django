# Generated by Djan 5.1.7 on 2025-04-01 13:57

from djan.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crudapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='Email',
            field=models.EmailField(default=None, max_length=100),
        ),
    ]

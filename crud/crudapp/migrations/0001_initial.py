# Generated by Djan 5.1.7 on 2025-04-01 13:50

from djan.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Employee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('FirstName', models.CharField(max_length=100)),
                ('LastName', models.CharField(max_length=100)),
                ('Title', models.CharField(max_length=50)),
                ('HasPassport', models.BooleanField(default=False)),
                ('Salary', models.IntegerField()),
                ('DateOfBirth', models.DateField()),
                ('HireDate', models.DateField()),
                ('Notes', models.CharField(max_length=200)),
                ('Country', models.CharField(choices=[('India', 'India'), ('USA', 'USA'), ('UK', 'UK'), ('Germany', 'Germany'), ('France', 'France'), ('Italy', 'Italy'), ('Spain', 'Spain'), ('Japan', 'Japan'), ('China', 'China'), ('Russia', 'Russia')], default=None, max_length=50)),
            ],
        ),
    ]

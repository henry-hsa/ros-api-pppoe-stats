# Generated by Django 4.1.1 on 2022-10-07 00:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor_app', '0005_listinterface'),
    ]

    operations = [
        migrations.AddField(
            model_name='listinterface',
            name='mac_address',
            field=models.CharField(max_length=255, null=True),
        ),
    ]

# Generated by Django 4.1.1 on 2022-10-06 03:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor_app', '0003_alter_userinfo_rx_upload_alter_userinfo_tx_download'),
    ]

    operations = [
        migrations.AddField(
            model_name='devicesinfo',
            name='serial_number',
            field=models.CharField(max_length=255, null=True),
        ),
    ]

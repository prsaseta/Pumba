# Generated by Django 2.0 on 2019-08-05 09:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0014_auto_20190727_1943'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='background',
            field=models.CharField(default='blue', max_length=100),
        ),
    ]

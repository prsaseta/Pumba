# Generated by Django 2.2.1 on 2019-05-29 16:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0008_gamekey_ai_count'),
    ]

    operations = [
        migrations.AddField(
            model_name='gamekey',
            name='capacity',
            field=models.PositiveSmallIntegerField(default=1),
            preserve_default=False,
        ),
    ]

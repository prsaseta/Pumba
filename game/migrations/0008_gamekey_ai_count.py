# Generated by Django 2.0 on 2019-05-07 12:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0007_gamekey_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='gamekey',
            name='ai_count',
            field=models.PositiveSmallIntegerField(default=1),
            preserve_default=False,
        ),
    ]

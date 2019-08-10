# Generated by Django 2.0 on 2019-08-10 09:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0018_gamekey_ai_difficulty'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gamekey',
            name='ai_difficulty',
            field=models.CharField(choices=[('EASY', 'Easy'), ('MEDIUM', 'Medium'), ('HARD', 'Hard')], default='EASY', max_length=20),
        ),
    ]

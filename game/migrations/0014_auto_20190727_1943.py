# Generated by Django 2.0 on 2019-07-27 17:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0013_auto_20190727_1943'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofilepicture',
            name='profile',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='game.UserProfile'),
        ),
    ]
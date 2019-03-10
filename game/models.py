from django.db import models

# Create your models here.

# Representa una partida en memoria
class GameKey(models.Model):
    key = models.CharField(max_length = 100)
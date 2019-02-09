from django.db import models

# Create your models here.

class PreRegister(models.Model):
    username = models.CharField(max_length = 100)
    password = models.CharField(max_length = 100)
    email = models.CharField(max_length = 500)
    verification = models.CharField(max_length = 100)
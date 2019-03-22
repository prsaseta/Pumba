import os
import django
from channels.routing import get_default_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pumba.settings")
os.environ['ASGI_THREADS']="4"
django.setup()
application = get_default_application()
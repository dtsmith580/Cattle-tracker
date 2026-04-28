from celery import Celery
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cattle_tracker.settings")

app = Celery("cattle_tracker_app")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

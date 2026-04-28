import os
from celery import Celery





# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cattle_tracker.settings')

# Create Celery application instance
app = Celery('cattle_tracker')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in Django apps
app.autodiscover_tasks()



@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
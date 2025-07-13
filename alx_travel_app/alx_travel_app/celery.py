import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_travel_app.settings')

# Create the Celery application
app = Celery('alx_travel_app')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Optional: Define a debug task
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


# Celery beat schedule (for periodic tasks if needed in the future)
app.conf.beat_schedule = {
    # Example periodic task - can be used for cleanup, reminders, etc.
    # 'cleanup-expired-bookings': {
    #     'task': 'listings.tasks.cleanup_expired_bookings',
    #     'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    # },
}

app.conf.timezone = 'UTC'
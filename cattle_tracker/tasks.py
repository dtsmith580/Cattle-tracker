from celery import shared_task
from django.utils.timezone import now
#from .models import Alert
from django.apps import apps
from datetime import timedelta
from .breeding_models import BreedingHistory

def get_alert_model():
    return apps.get_model('cattle_tracker', 'Alert')

@shared_task
def check_due_alerts():
    alerts = Alert.objects.filter(alert_date__lte=now(), resolved=False)
    for alert in alerts:
        print(f"🚨 ALERT: {alert.message}")  # Replace with actual notification logic
        alert.resolved = True
        alert.save()

@shared_task
def check_breeding_alerts():
    today = now().date()

    alerts = []
    
    # Alert for pregnancy confirmation check (30 days after breeding)
    confirm_due_date = today - timedelta(days=30)
    confirm_due_cows = BreedingHistory.objects.filter(
        breeding_date__lte=confirm_due_date, 
        pregnancy_confirmation_date__isnull=True
    )

    for record in confirm_due_cows:
        alerts.append(f"Pregnancy confirmation due for cow {record.cow.ear_tag}")

    # Alert for upcoming calving (14 days before expected calving)
    calving_alert_date = today + timedelta(days=14)
    calving_due_cows = BreedingHistory.objects.filter(
        expected_calving_date__lte=calving_alert_date,
        expected_calving_date__gte=today,
        calving_outcome__isnull=True
    )

    for record in calving_due_cows:
        alerts.append(f"Calving expected soon for cow {record.cow.ear_tag}")

    return alerts if alerts else "No alerts today."
       


@shared_task
def breeding_alert_task():
    Alert = get_alert_model()  # Import the model dynamically
    alerts = Alert.objects.all()
    print(f"Processing {alerts.count()} breeding alerts.")
    return "Breeding alert task executed successfully"
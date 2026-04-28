from django.db.models.signals import post_save,  post_delete
from django.dispatch import receiver
from django.utils.timezone import now, timedelta
from .models.breeding_models import BreedingRecord, PregnancyRecord
from .models.alert_models import Alert
from cattle_tracker_app.models import Paddock

# Auto-create an alert when a cow is bred
@receiver(post_save, sender=BreedingRecord)
def create_pregnancy_check_alert(sender, instance, created, **kwargs):
    if created:
        alert_date = instance.breeding_date + timedelta(days=30)  # Pregnancy check in 30 days
        Alert.objects.create(
            cattle=instance.cow,
            alert_type='pregnancy_check',
            message=f"Time to check if {instance.cow.ear_tag} is pregnant.",
            alert_date=alert_date
        )


@receiver(post_save, sender=PregnancyRecord)
def create_calving_reminder_alert(sender, instance, created, **kwargs):
    if instance.pregnancy_confirmed and instance.expected_due_date:
        alert_date = instance.expected_due_date - timedelta(days=7)  # Notify 1 week before due date
        Alert.objects.create(
            cattle=instance.cow,
            alert_type='calving_reminder',
            message=f"{instance.cow.ear_tag} is due to calve soon! Expected date: {instance.expected_due_date}.",
            alert_date=alert_date
        )
@receiver(post_save, sender=PregnancyRecord)
def create_missed_pregnancy_alert(sender, instance, **kwargs):
    if not instance.pregnancy_confirmed:
        breeding_record = instance.breeding_record
        if (now().date() - breeding_record.breeding_date).days > 60:  # 60 days passed
            Alert.objects.create(
                cattle=instance.cow,
                alert_type='missed_pregnancy',
                message=f"Pregnancy for {instance.cow.ear_tag} was not confirmed within 60 days.",
                alert_date=now()
            )
@receiver(post_save, sender=Paddock)
def update_pasture_on_paddock_save(sender, instance, **kwargs):
    if instance.pasture:
        instance.pasture.update_acres_and_paddocks()

@receiver(post_delete, sender=Paddock)
def update_pasture_on_paddock_delete(sender, instance, **kwargs):
    if instance.pasture:
        instance.pasture.update_acres_and_paddocks()
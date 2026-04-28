from django.db import models

class ToDoBoard(models.Model):
    """Dummy model to expose a sidebar entry in Django Admin."""
    class Meta:
        managed = True            # <-- was False
        app_label = "cattle_tracker_app"
        verbose_name = "Project To-Do"
        verbose_name_plural = "Project To-Do"

    def __str__(self):
        return "Project To-Do"

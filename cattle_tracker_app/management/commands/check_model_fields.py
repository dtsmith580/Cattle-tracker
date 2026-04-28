from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connection

class Command(BaseCommand):
    help = 'Checks all models for fields missing in the database schema.'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            for model in apps.get_models():
                db_table = model._meta.db_table
                model_fields = [f.column for f in model._meta.fields]
                # Get actual DB columns
                cursor.execute(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name=%s AND table_schema='public'
                    """, [db_table]
                )
                db_columns = set(row[0] for row in cursor.fetchall())

                missing = []
                for field in model_fields:
                    if field not in db_columns:
                        missing.append(field)

                if missing:
                    self.stdout.write(self.style.ERROR(
                        f"Table '{db_table}' missing columns: {', '.join(missing)}"
                    ))
                else:
                    self.stdout.write(self.style.SUCCESS(
                        f"Table '{db_table}' is in sync."
                    ))

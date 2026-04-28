import csv
import io
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from cattle_tracker_app.models.cattle_models import Cattle
from cattle_tracker_app.models.importlog_models import ImportLog

CATTLE_FIELDS = ['ear_tag', 'dob', 'sex', 'breed', 'status']

def upload_csv_view(request):
    if request.method == 'POST' and 'csv_file' in request.FILES:
        csv_file = request.FILES['csv_file']
        decoded = csv_file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))

        csv_headers = reader.fieldnames
        preview_rows = [row for _, row in zip(range(5), reader)]

        request.session['csv_data'] = decoded
        request.session['csv_headers'] = csv_headers

        return render(request, 'import_csv/map_fields.html', {
            'csv_headers': csv_headers,
            'model_fields': CATTLE_FIELDS,
            'preview': preview_rows,
        })

    return render(request, 'import_csv/upload.html')
    
    
SIRE_TYPE_MAP = {
    'donor': 'donor',
    'donor bull': 'donor',
    'owned': 'owned',
    'owned animal': 'owned',
    'leased': 'leased',
    'leased sire': 'leased',
}

def normalize_sire_type(value):
    if not value:
        return 'owned'  # default
    cleaned = value.strip().lower()
    return SIRE_TYPE_MAP.get(cleaned, 'owned')

def confirm_import_view(request):
    if request.method == 'POST':
        header_count = int(request.POST.get('header_count'))
        field_mapping = {}

        for i in range(header_count):
            selected_field = request.POST.get(f'field_{i}')
            if selected_field:
                field_mapping[i] = selected_field

        raw_csv = request.session.get('csv_data')
        decoded = io.StringIO(raw_csv)
        reader = csv.reader(decoded)
        headers = next(reader)

        imported = 0
        failed = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):  # CSV header is line 1
            cattle_data = {}
            for idx, model_field in field_mapping.items():
                value = row[idx].strip()

                # Handle special fields
                if model_field == 'sire_type':
                    value = normalize_sire_type(value)
                elif model_field == 'dob':
                    from datetime import datetime
                    try:
                        value = datetime.strptime(value, '%Y-%m-%d').date()
                    except ValueError:
                        errors.append(f"Invalid date '{value}' on row {row_num}")
                        failed += 1
                        value = None

                cattle_data[model_field] = value

            try:
                if 'dob' not in cattle_data or not cattle_data['dob']:
                    raise ValueError("Missing or invalid DOB")

                Cattle.objects.create(**cattle_data)
                imported += 1
            except Exception as e:
                failed += 1
                errors.append(f"Row {row_num}: {str(e)}")

        return render(request, 'import_csv/import_result.html', {
            'imported': imported,
            'failed': failed,
            'errors': errors,
        })

    return redirect('import_csv')
    
    ImportLog.objects.create(
    filename=request.FILES.get('csv_file').name if 'csv_file' in request.FILES else 'N/A',
    imported_by=request.user if request.user.is_authenticated else None,
    record_type='Cattle',
    success_count=imported,
    failure_count=failed,
    error_log="\n".join(errors[:10])  # Log only first 10 errors to avoid overflow
)
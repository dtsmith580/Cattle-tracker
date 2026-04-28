# views/report_views.py
import openpyxl
from openpyxl.styles import Font
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from cattle_tracker_app.models import Cattle,Owner
from datetime import datetime
import csv
from django.http import HttpResponse
from django.db.models import Sum
from django.db.models.functions import ExtractYear
from dateutil.relativedelta import relativedelta


@staff_member_required
def cattle_sales_report(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    calendar_year = request.GET.get('year')

    sales = Cattle.objects.filter(status='sold')

    if calendar_year:
        sales = sales.filter(sale_date__year=calendar_year)
    elif start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            sales = sales.filter(sale_date__range=(start, end))
        except ValueError:
            sales = []

    # ✅ Inject age at sale into each cattle object
    for cattle in sales:
        if cattle.dob and cattle.sale_date:
            delta = relativedelta(cattle.sale_date, cattle.dob)
            y, m = delta.years, delta.months
            if y and m:
                cattle.age_at_sale = f"{y}y {m}m"
            elif y:
                cattle.age_at_sale = f"{y}y"
            elif m:
                cattle.age_at_sale = f"{m}m"
            else:
                cattle.age_at_sale = "0m"
        else:
            cattle.age_at_sale = "—"

    total_sales = sales.aggregate(total=Sum('sale_price'))['total'] or 0

    years = (
    Cattle.objects.filter(status='sold', sale_date__isnull=False)
    .dates('sale_date', 'year')
    )

    return render(request, 'reports/cattle_sales_report.html', {
        'sales': sales,
        'start_date': start_date,
        'end_date': end_date,
        'calendar_year': calendar_year,
        'total_sales': total_sales,
        'years': years,
    })


def cattle_sales_csv(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if not start_date or not end_date:
        return HttpResponse("Missing start or end date", status=400)

    sales = Cattle.objects.filter(status='sold', sale_date__range=(start_date, end_date)).order_by('sale_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="cattle_sales_{start_date}_to_{end_date}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Ear Tag', 'Owner', 'Sale Date', 'Animal Type', 'Notes'])

    for c in sales:
        writer.writerow([
            c.ear_tag,
            str(c.owner) if c.owner else '',
            c.sale_date.strftime('%Y-%m-%d') if c.sale_date else '',
            c.animal_type,
            c.notes or '',
        ])

    return response
    
def cattle_sales_pdf(request):
    return HttpResponse("PDF generation not yet implemented", content_type="text/plain")

def cattle_sales_excel(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if not start_date or not end_date:
        return HttpResponse("Missing start or end date", status=400)

    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        return HttpResponse("Invalid date format", status=400)

    sales = Cattle.objects.filter(status='sold', sale_date__range=(start, end)).order_by('sale_date')

    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cattle Sales"

    headers = ["Ear Tag", "Owner", "Sale Date", "Animal Type", "Sale Price", "Notes"]
    ws.append(headers)

    for cell in ws[1]:
        cell.font = Font(bold=True)

    for c in sales:
        ws.append([
            c.ear_tag,
            str(c.owner) if c.owner else '',
            c.sale_date.strftime('%Y-%m-%d') if c.sale_date else '',
            c.animal_type,
            c.sale_price if c.sale_price else '',
            c.notes or ''
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="cattle_sales_{start_date}_to_{end_date}.xlsx"'

    wb.save(response)
    return response


def cattle_sales_print(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    sales = Cattle.objects.filter(status='sold')

    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            sales = sales.filter(sale_date__range=(start, end))
        except ValueError:
            pass

    return render(request, 'reports/cattle_list_export.html', {
        'cattle_list': sales,
        'print_mode': True,
    })

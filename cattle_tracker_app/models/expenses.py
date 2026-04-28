# cattle_tracker_app/models/expenses.py
from django.db import models
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    tax_deductible = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Receipt(models.Model):
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    vendor = models.CharField(max_length=200, blank=True)
    date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=10, default='USD')
    total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    raw_text = models.TextField(blank=True)  # full OCR text
    source_file = models.FileField(upload_to='receipts/%Y/%m/%d/')
    confirmed = models.BooleanField(default=False)  # user verified parsed fields
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.vendor or 'Receipt'} — {self.date or self.uploaded_at.date()}"

class ReceiptLineItem(models.Model):
    receipt = models.ForeignKey(Receipt, related_name='line_items', on_delete=models.CASCADE)
    description = models.CharField(max_length=300, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    # Link to your existing models:
    cattle = models.ForeignKey('Cattle', null=True, blank=True, on_delete=models.SET_NULL)
    pasture = models.ForeignKey('Pasture', null=True, blank=True, on_delete=models.SET_NULL)
    owner = models.ForeignKey('Owner', null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return f"{self.description} — {self.amount}"

class ReceiptAudit(models.Model):
    receipt = models.ForeignKey(Receipt, related_name='audits', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)  # 'uploaded', 'ocr_parsed', 'edited', 'confirmed'
    timestamp = models.DateTimeField(auto_now_add=True)
    detail = models.TextField(blank=True)

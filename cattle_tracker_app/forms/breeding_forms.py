from django import forms
from datetime import date
from dateutil.relativedelta import relativedelta
from cattle_tracker_app.models.cattle_models import Cattle
from cattle_tracker_app.models.herd_sire_models import HerdSire
from cattle_tracker_app.models.breeding_models import BreedingRecord
from cattle_tracker_app.models.breeding_models import BreedingHistory
from cattle_tracker_app.models.leasedbull_models import LeasedBull

from django.utils.html import format_html
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from cattle_tracker_app.models.breeding_models import BreedingRecord
#from cattle_tracker_app.forms.breeding_forms import BreedingHistoryAdminForm
from cattle_tracker_app.utils.access import get_user_allowed_owners

class BreedingRecordForm(forms.ModelForm):
    class Meta:
        model = BreedingRecord
        fields = '__all__'
        widgets = {
            'breeding_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # Ensure fields are initialized before filtering
        print("🐛 __init__ is running!")  # Add this
        
        today = date.today()
        cow_cutoff = today - relativedelta(months=13)
        bull_cutoff = today - relativedelta(months=16)
        print(f"🐄 Cow cutoff date:")
        
        print(f"🐄 Cow cutoff date: {cow_cutoff}")
        print(f"🐂 Bull cutoff date: {bull_cutoff}")

        cow_qs = Cattle.objects.filter(
            sex='female',
            animal_type__in=['heifer', 'cow'],
            dob__lte=cow_cutoff
        )

        bull_qs = Cattle.objects.exclude(animal_type='steer').filter(
            sex='male',
            dob__lte=bull_cutoff
        )

        print("🧬 Filtered cows:")
        for cow in cow_qs:
            print(f"- {cow.ear_tag}: {cow.dob} ({cow.animal_type})")

        print("🧬 Filtered bulls:")
        for bull in bull_qs:
            print(f"- {bull.ear_tag}: {bull.dob} ({bull.animal_type})")

        self.fields['cow'].queryset = cow_qs
        self.fields['bull'].queryset = bull_qs
        self.fields['cleanup_sire'].queryset = bull_qs

        self.fields['herd_sire'].queryset = HerdSire.objects.all().order_by('name')
        self.fields['cleanup_herd_sire'].queryset = HerdSire.objects.all().order_by('name')
        
class BreedingHistoryAdminForm(forms.ModelForm):
    is_leased = forms.BooleanField(required=False, label="Use Leased Bull")

    class Meta:
        model = BreedingRecord
        fields = ['cow', 'breeding_date', 'method', 'bull', 'herd_sire', 'is_leased']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['breeding_date'].widget = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        # Filter cows and heifers
        self.fields['cow'].queryset = Cattle.objects.filter(
            sex='female',
            status='alive',
            animal_type__in=['cow', 'heifer']
        ).order_by('ear_tag')

        # Age filter using relativedelta
        bull_cutoff = date.today() - relativedelta(months=16)

        # Determine if leased bull checkbox is checked
        show_leased = False
        if 'data' in kwargs:
            show_leased = kwargs['data'].get("is_leased") in ['on', 'true', '1']
        elif hasattr(self, 'data'):
            show_leased = self.data.get("is_leased") in ['on', 'true', '1']

        # 🐂 Debug info
        print(f"🐂 Show Leased: {show_leased} Form Data: {getattr(self, 'data', {})}")

        # Get cattle bulls and leased bulls
        if show_leased:
            leased_bulls = [(f"leased-{bull.id}", f"{bull.ear_tag} (Leased)") for bull in LeasedBull.objects.all()]
            bull_choices = [('', '---------')] + leased_bulls
        else:
            owned_bulls = Cattle.objects.filter(
                animal_type='bull',
                status='alive',
                dob__lte=bull_cutoff
            ).values_list('id', 'ear_tag')
            bull_choices = [('', '---------')] + list(owned_bulls)

        self.fields['bull'].choices = bull_choices
        self.fields['bull'].required = False

        # Herd sire filtering
        self.fields['herd_sire'].queryset = HerdSire.objects.all().order_by('name')
        self.fields['herd_sire'].required = False

# AJAX utility for live updating bull field
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required

@login_required
@require_GET
def get_bull_options(request):
    show_leased = request.GET.get("is_leased") in ['on', 'true', '1']
    bull_cutoff = date.today() - relativedelta(months=16)

    if show_leased:
        bulls = [(f"leased-{bull.id}", f"{bull.ear_tag} (Leased)") for bull in LeasedBull.objects.all()]
    else:
        bulls = list(Cattle.objects.filter(
            animal_type='bull',
            status='alive',
            dob__lte=bull_cutoff
        ).values_list('id', 'ear_tag'))

    return JsonResponse({"bulls": bulls})



        
@login_required
def add_breeding_record_view(request):
    form = BreedingHistoryAdminForm(request.POST or None)

    if form.is_valid():
        instance = form.save(commit=False)
        allowed_owners = get_user_allowed_owners(request.user)
        if instance.cow.owner in allowed_owners:
            instance.save()
            messages.success(request, "✅ Breeding record added.")
            return redirect('cattle_list')
        else:
            messages.error(request, "❌ You don't have permission to add records for this animal.")

    return render(request, "breeding/add_breeding_record.html", {
        "form": form,
    })

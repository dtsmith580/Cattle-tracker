from django.views.generic import ListView, DetailView
from cattle_tracker_app.models.leasedbull_models import LeasedBull
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from cattle_tracker_app.models import LeasedBull
from cattle_tracker_app.forms.leasedbull_forms import LeasedBullForm
from django.shortcuts import render, redirect

from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse


class LeasedBullListView(ListView):
    model = LeasedBull
    template_name = 'cattle/leased_bull_list.html'
    context_object_name = 'leased_bulls'

class LeasedBullDetailView(DetailView):
    model = LeasedBull
    template_name = 'cattle/leased_bull_detail.html'
    context_object_name = 'leased_bull'
    

@csrf_exempt
def update_leased_bull_field(request, pk):
    if request.method == 'POST':
        leased_bull = LeasedBull.objects.get(pk=pk)

        # 🗑️ Handle image deletion
        if request.POST.get('delete_image') == '1':
            if leased_bull.image:
                leased_bull.image.delete(save=False)
                leased_bull.image = None
                leased_bull.save()
            return JsonResponse({'success': True})

        # 📸 Handle image upload
        if request.POST.get('field') == 'image' and 'image' in request.FILES:
            leased_bull.image = request.FILES['image']
            leased_bull.save()
            return JsonResponse({'success': True})

        # 🔤 Handle text/date field updates
        field = request.POST.get('field')
        value = request.POST.get('value')

        if field in ['ear_tag', 'breed', 'dob', 'owner_name', 'lease_start', 'lease_end']:
            setattr(leased_bull, field, value)
            leased_bull.save()
            return JsonResponse({'success': True})

        return JsonResponse({'error': 'Invalid field'}, status=400)

@csrf_exempt
def create_leased_bull(request):
    if request.method == 'POST':
        form = LeasedBullForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('leased_bull_list')  # or your actual list view name
    else:
        form = LeasedBullForm()
    return render(request, 'cattle/leased_bull_form.html', {'form': form})
    
def delete_leased_bull(request, pk):
    leased_bull = get_object_or_404(LeasedBull, pk=pk)
    leased_bull.delete()
    return HttpResponseRedirect(reverse('leased_bull_list'))
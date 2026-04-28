# views/herd_sire_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from cattle_tracker_app.models.herd_sire_models import HerdSire
from cattle_tracker_app.forms.herd_sire_forms import HerdSireForm
from django.http import HttpResponseRedirect
from django.urls import reverse


def herd_sire_list(request):
    herd_sires = HerdSire.objects.all()
    return render(request, 'cattle/herd_sire_list.html', {'herd_sires': herd_sires})

def herd_sire_detail(request, pk):
    herd_sire = get_object_or_404(HerdSire, pk=pk)
    form = HerdSireForm(instance=herd_sire)
    return render(request, 'cattle/herd_sire_detail.html', {'herd_sire': herd_sire, 'form': form})

@require_POST
def herd_sire_update(request, pk):
    herd_sire = get_object_or_404(HerdSire, pk=pk)

    # Handle image deletion
    if request.POST.get("delete_image") == "1":
        herd_sire.image.delete(save=True)
        return JsonResponse({"success": True})

    form = HerdSireForm(request.POST, request.FILES, instance=herd_sire)
    if form.is_valid():
        form.save()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "errors": form.errors})

@require_POST
def herd_sire_delete(request, pk):
    herd_sire = get_object_or_404(HerdSire, pk=pk)
    herd_sire.delete()
    return redirect('herd_sire_list')
    
    
def herd_sire_create(request):
    if request.method == 'POST':
        form = HerdSireForm(request.POST)
        if form.is_valid():
            herd_sire = form.save()
            return HttpResponseRedirect(reverse('herd_sire_detail', args=[herd_sire.pk]))
    else:
        form = HerdSireForm()

    return render(request, 'cattle/herd_sire_form.html', {'form': form})
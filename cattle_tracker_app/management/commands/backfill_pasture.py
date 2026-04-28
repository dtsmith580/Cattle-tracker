for pasture in Pasture.objects.all():
    if pasture.geometry and not pasture.boundary:
        pasture.boundary = pasture.geometry
        pasture.save()
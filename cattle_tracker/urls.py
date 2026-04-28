from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from cattle_tracker_app.views.dashboard import root_redirect_view
from django.shortcuts import redirect
from cattle_tracker_app.views.dashboard import access_denied_view
from django.conf import settings
from django.conf.urls.static import static
#from cattle_tracker_app.views.breeding_views import add_breeding_record_view

def root_redirect_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')  # named URL
    return redirect('login')

urlpatterns = [
    
    path("accounts/", include("django.contrib.auth.urls")),  # ✅ add this
    path('', root_redirect_view),  # 👈 this handles /
   
    path('accounts/login/', auth_views.LoginView.as_view(template_name='templates/registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    #path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('', include('cattle_tracker_app.urls')),  # Make sure this line is present
    path("access-denied/", access_denied_view, name="access_denied"),
    #path('breeding/add/', add_breeding_record_view, name='add_breeding_record'),

] 
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

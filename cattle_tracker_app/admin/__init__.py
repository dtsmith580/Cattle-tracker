from .alert_admin import *
from .cattle_admin import *
from .breeding_admin import *
from .herdsire_admin import *
from .importlog_admin import *
from .leasedbull_admin import *
from .owner_admin import *  # 👈 Make sure this is here
from .turnout_admin import *
from .weight_admin import *
from .paddock_admin import *
from .settings_admin import *
#from .pasture_admin import *
from .todo_admin import *
from .health_admin import * 

from django.contrib import admin as dj_admin

# Use custom templates that extend the stock admin ones
dj_admin.site.index_template = "admin/index.html"
dj_admin.site.app_index_template = "admin/custom_app_index.html"

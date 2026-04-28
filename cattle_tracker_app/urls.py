from django.contrib import admin
from django.urls import path, include

# -----------------------------
# Dashboard & Settings
# -----------------------------
from cattle_tracker_app.views.dashboard import dashboard_view
from cattle_tracker_app.views.import_csv import upload_csv_view, confirm_import_view
from cattle_tracker_app.views.settings_views import edit_ranch_settings
from cattle_tracker_app.views.settings_alert_views import alerts_settings_view
from cattle_tracker_app.views import alert_views

# -----------------------------
# Cattle
# -----------------------------
from cattle_tracker_app.views import (
    CattleDetailView,
    cattle_list_view,
    add_cattle_view,
    CattleCreateView,
    CattleUpdateView,
    delete_cattle_view,
    export_cattle_csv,
    mark_cattle_sold,
    mark_cattle_dead,
    bulk_mark_cattle_sold,
    add_weight_log,
    cattle_card_partial,
    update_cattle_field,
)

# -----------------------------
# Health
# -----------------------------
from cattle_tracker_app.views.health_views import (
    health_list, health_create, health_edit, health_delete,
    cattle_health_list, herd_vaccination,
)

# -----------------------------
# Leased Bulls
# -----------------------------
from cattle_tracker_app.views.leasedbull_views import (
    LeasedBullListView,
    LeasedBullDetailView,
    update_leased_bull_field,
    create_leased_bull,
    delete_leased_bull,
)

# -----------------------------
# Bull Pen
# -----------------------------
from cattle_tracker_app.views import bull_pen_views

# -----------------------------
# Herd Sires
# -----------------------------
from cattle_tracker_app.views.herd_sire_views import (
    herd_sire_list,
    herd_sire_create,
    herd_sire_detail,
    herd_sire_delete,
    herd_sire_update,
)

# -----------------------------
# Breeding
# -----------------------------
from cattle_tracker_app.forms.breeding_forms import get_bull_options
from cattle_tracker_app.views.breeding_views import (
    breeding_history_view,
    breeding_admin_view,
    edit_breeding_record,
    delete_breeding_record,
)

# -----------------------------
# Turnout Groups
# -----------------------------
from cattle_tracker_app.views.turnout_views import (
    TurnoutGroupListView,
    TurnoutGroupCreateView,
    TurnoutGroupDetailView,
    TurnoutGroupUpdateView,
)

# -----------------------------
# Reports
# -----------------------------
from cattle_tracker_app.views.report_views import (
    cattle_sales_report,
    cattle_sales_csv,
    cattle_sales_pdf,
    cattle_sales_excel,
    cattle_sales_print,
)

# -----------------------------
# Pastures & Paddocks
# -----------------------------
from cattle_tracker_app.views.pasture_views import (
    PastureDetailView,
    pasture_update_field,
    pasture_list_page,
    pasture_create_view,
)

from cattle_tracker_app.views.paddock_views import (
    PaddockDetailView,
    paddock_update_field,
    paddock_create_view,
    paddock_update_boundary,
)

# =========================================================
# URLPATTERNS
# =========================================================

urlpatterns = [

    # -----------------------------
    # Admin & Dashboard
    # -----------------------------
    path("admin/", admin.site.urls),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("settings/", edit_ranch_settings, name="edit_ranch_settings"),

    # -----------------------------
    # Alerts
    # -----------------------------
    path("alerts/", alert_views.alerts_inbox_view, name="alerts_inbox"),
    path("alerts/<int:pk>/resolve/", alert_views.alert_resolve_view, name="alert_resolve"),
    path("alerts/<int:pk>/snooze/", alert_views.alert_snooze_view, name="alert_snooze"),
    path("alerts/rules/", alert_views.alert_rules_list_view, name="alert_rules_list"),
    path("alerts/rules/new/", alert_views.alert_rule_create_view, name="alert_rule_create"),
    path("alerts/rules/<int:pk>/edit/", alert_views.alert_rule_edit_view, name="alert_rule_edit"),
    path("alerts/rules/<int:pk>/toggle/", alert_views.alert_rule_toggle_view, name="alert_rule_toggle"),
    path("settings/alerts/", alerts_settings_view, name="alert_settings"),

    # -----------------------------
    # CSV Import
    # -----------------------------
    path("import-csv/", upload_csv_view, name="import_csv"),
    path("import-csv/confirm/", confirm_import_view, name="import_csv_confirm"),

    # -----------------------------
    # Cattle
    # -----------------------------
    path("cattle/", cattle_list_view, name="cattle_list"),
    path("cattle/add/", add_cattle_view, name="add_cattle"),
    path("cattle/<int:pk>/", CattleDetailView.as_view(), name="view_cattle"),
    path("cattle/new/", CattleCreateView.as_view(), name="create_cattle"),
    path("cattle/<int:pk>/edit/", CattleUpdateView.as_view(), name="edit_cattle"),
    path("cattle/<int:pk>/delete/", delete_cattle_view, name="delete_cattle"),

    path("cattle/bulk-mark-sold/", bulk_mark_cattle_sold, name="bulk_mark_cattle_sold"),
    path("cattle/export/", export_cattle_csv, name="export_cattle_csv"),
    path("cattle/<int:pk>/card/", cattle_card_partial, name="cattle_card_partial"),
    path("cattle/<int:pk>/update-field/", update_cattle_field, name="update_cattle_field"),
    path("cattle/<int:pk>/add-weight-log/", add_weight_log, name="add_weight_log"),

    # -----------------------------
    # Health
    # -----------------------------
    path("health/", health_list, name="health_list"),
    path("health/add/<int:cattle_pk>/", health_create, name="health_add"),
    path("health/<int:cattle_pk>/edit/", health_edit, name="health_edit"),
    path("health/<int:cattle_pk>/delete/", health_delete, name="health_delete"),
    path("cattle/<int:cattle_pk>/health/", cattle_health_list, name="cattle_health_list"),
    path("cattle/<int:cattle_pk>/health/add/", health_create, name="health_create_for_cattle"),
    path("health/herd-vaccination/", herd_vaccination, name="herd_vaccination"),

    # -----------------------------
    # Leased Bulls
    # -----------------------------
    path("leased-bulls/", LeasedBullListView.as_view(), name="leased_bull_list"),
    path("leased-bulls/<int:pk>/", LeasedBullDetailView.as_view(), name="leased_bull_detail"),
    path("leased-bulls/<int:pk>/update-field/", update_leased_bull_field, name="update_field"),
    path("leased-bulls/add/", create_leased_bull, name="create_leased_bull"),
    path("leased-bulls/<int:pk>/delete/", delete_leased_bull, name="delete_leased_bull"),

    # -----------------------------
    # Bull Pen
    # -----------------------------
    path("bull-pen/", bull_pen_views.bull_pen_list, name="bull_pen_list"),
    path("bull-pen/add/", bull_pen_views.herd_bull_create, name="herd_bull_create"),
    path("bull-pen/<int:pk>/", bull_pen_views.herd_bull_detail, name="herd_bull_detail"),
    path("bull-pen/<int:pk>/edit/", bull_pen_views.herd_bull_edit, name="herd_bull_edit"),

    # -----------------------------
    # Herd Sires
    # -----------------------------
    path("herd-sires/", herd_sire_list, name="herd_sire_list"),
    path("herd-sires/new/", herd_sire_create, name="herd_sire_create"),
    path("herd-sires/<int:pk>/", herd_sire_detail, name="herd_sire_detail"),
    path("herd-sires/<int:pk>/delete/", herd_sire_delete, name="herd_sire_delete"),
    path("herd-sires/<int:pk>/update/", herd_sire_update, name="herd_sire_update"),

    # -----------------------------
    # Breeding
    # -----------------------------
    path("breedinghistory/", breeding_history_view, name="breeding_history"),
    path("breeding/admin/", breeding_admin_view, name="breeding_admin"),
    path("breeding/edit/<int:pk>/", edit_breeding_record, name="edit_breeding_record"),
    path("breeding/delete/<int:pk>/", delete_breeding_record, name="delete_breeding_record"),
    path("ajax/get-bull-options/", get_bull_options, name="get_bull_options"),

    # -----------------------------
    # Turnout Groups
    # -----------------------------
    path("turnout-groups/", TurnoutGroupListView.as_view(), name="turnoutgroup_list"),
    path("turnout-groups/add/", TurnoutGroupCreateView.as_view(), name="add_turnout_group"),
    path("turnout-groups/<int:pk>/", TurnoutGroupDetailView.as_view(), name="turnoutgroup_detail"),
    path("turnout-groups/<int:pk>/edit/", TurnoutGroupUpdateView.as_view(), name="turnoutgroup_edit"),

    # -----------------------------
    # Reporting
    # -----------------------------
    path("reports/cattle-sales/", cattle_sales_report, name="cattle_sales_report"),
    path("reports/cattle-sales/export-csv/", cattle_sales_csv, name="cattle_sales_csv"),
    path("reports/cattle-sales/export-pdf/", cattle_sales_pdf, name="cattle_sales_pdf"),
    path("reports/cattle-sales/export-excel/", cattle_sales_excel, name="cattle_sales_excel"),
    path("reports/cattle-sales/export-print/", cattle_sales_print, name="cattle_sales_print"),

    # -----------------------------
    # Pastures & Paddocks
    # -----------------------------
    path("pastures/", pasture_list_page, name="pasture_list"),
    path("pastures/new/", pasture_create_view, name="pasture_create"),
    path("paddocks/new/", paddock_create_view, name="paddock_create"),

    path("pastures/<int:pk>/", PastureDetailView.as_view(), name="pasture_detail"),
    path("pastures/<int:pk>/update/", pasture_update_field, name="pasture_update_field"),

    path("pastures/paddock/<int:pk>/", PaddockDetailView.as_view(), name="paddock_detail"),
    path("pastures/paddock/<int:pk>/update/", paddock_update_field, name="paddock_update_field"),
    path("pastures/paddock/<int:pk>/boundary/", paddock_update_boundary, name="paddock_update_boundary"),

    # -----------------------------
    # API (Isolated to avoid circular imports)
    # -----------------------------
    path("api/", include("cattle_tracker_app.api.urls")),
]
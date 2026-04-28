from django.contrib import admin
from django.utils.safestring import mark_safe
from django.conf import settings
from pathlib import Path
import markdown

from cattle_tracker_app.models.misc_models import ToDoBoard

@admin.register(ToDoBoard)
class ToDoBoardAdmin(admin.ModelAdmin):
    change_list_template = "admin/todo_changelist.html"

    # Read-only: hide add/change/delete everywhere
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        md_path = Path(settings.BASE_DIR) / "TODO.md"
        if md_path.exists():
            md_text = md_path.read_text(encoding="utf-8")
        else:
            md_text = (
                "# 📝 Cattle Tracker To-Do / Polish List\n\n"
                "_This TODO.md doesn’t exist yet. Create one at project root to populate this page._\n\n"
                "## Forms & UI\n- [ ] Example item"
            )

        html = markdown.markdown(md_text, extensions=["extra", "tables", "sane_lists"])
        context = {
            "title": "Project To-Do",
            "todo_html": mark_safe(html),  # trusted local file; if you prefer, sanitize with bleach
        }
        return super().changelist_view(request, extra_context=context)

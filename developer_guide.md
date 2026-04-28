
# 🐄 Cattle Tracker App — Developer Guide

Welcome to the modular Django-based Cattle Tracker App. This guide outlines the folder structure and best practices used in the project.

---

## 📁 Project Structure Overview

```
cattle_tracker_app/
├── admin/              # Modular Django admin registrations
├── constants/          # Choices, limits, and display labels for models and forms
├── forms/              # Modular Django forms
├── models/             # Modular Django model definitions
├── static/             # Static files (JS, CSS)
├── templates/          # HTML templates organized by feature
├── templatetags/       # Custom template filters (e.g., group access)
├── utils/              # Shared utility functions for access control and roles
├── views/              # Modular Django views
├── migrations/         # Django migration history
├── celery_config.py    # Background task setup
├── urls.py             # App-level URL configuration
├── signals.py          # Signal hooks for model events
├── __init__.py         # App config
```

---

## ✅ Admin Modules

Located in `admin/`:

- `cattle_admin.py`: Admin config for `Cattle`
- `leasedbull_admin.py`: Admin config for `LeasedBull`
- `weight_admin.py`: Admin config for `WeightLog`
- `owner_admin.py`: Admin config for `Owner` + inline user access
- `herdsire_admin.py`: Admin config for `HerdSire`
- `breeding_admin.py`: Admin config for `BreedingHistory`
- `turnout_admin.py`: Admin config for `TurnoutGroup`
- `importlog_admin.py`: Admin config for CSV imports

All loaded via `admin/__init__.py`.

---

## ✅ Models Directory

Located in `models/` and auto-imported from `models/__init__.py`. This includes:

- `cattle_models.py`
- `breeding_models.py`
- `leasedbull_models.py`
- `health_models.py`
- `weight_models.py`
- `ownership_models.py`
- `herd_sire_models.py`
- `turnout_models.py`
- `alert_models.py`
- `importlog_models.py`

---

## ✅ Forms Directory

Located in `forms/`, including:

- `cattle_forms.py`
- `breeding_forms.py`
- `turnout_forms.py`
- `health_forms.py`
- `weight_forms.py`
- `ownership_forms.py`

---

## ✅ Views Directory

Organized by feature in `views/`:

- `cattle_views.py`
- `breeding_views.py`
- `turnout_views.py`
- `dashboard.py`
- `import_csv.py`

---

## 🧠 Utility Modules

In `utils/`, used for role enforcement and access filtering:

- `access.py`
- `roles.py`

---

## 🧩 Constants

Stored in `constants/` for maintainable dropdowns and business logic:

- `choices.py`
- `labels.py`
- `limits.py`

---

## 🧪 Testing

Tests can be added in `tests.py` or modularized in a future `tests/` folder.

---

## 🛠 Suggestions for New Devs

- Register new models by adding a file in `models/` and importing it in `models/__init__.py`
- Follow existing modular patterns for `forms/`, `views/`, and `admin/`
- Use `utils/` for shared logic
- Use `constants/` for any field choices or business logic limits
- Use `templatetags/` for group-based permissions and custom display logic

---

Happy hacking! 🐮

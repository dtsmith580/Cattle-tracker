# 📝 Cattle Tracker To-Do / Polish List

This file tracks polish items, minor fixes, and nice-to-have features.  
Update as tasks are completed or new ones are added.

---

## Forms & UI
- [ ] Grey out or hide inactive **pastures/paddocks** in dropdowns so users can’t select them.
- [ ] Polish **sidebar layout** (spacing, icons, active link highlighting).
- [ ] Improve **cattle detail view**:
  - [ ] Align profile card sizes (match herd sire/leased bull detail).
  - [ ] Keep image next to fields instead of stacked.
  - [ ] Hide upload/delete buttons until ✏️ edit mode.
  - [ ] Add inline editing & saving for profile fields.
- [ ] Standardize **form layouts** (labels and fields on the same line, consistent spacing).
- [ ] Shorten width of input fields so they don’t span the whole card.

## Admin
- [ ] Add **inline add/edit** for notes, alerts, or weight logs directly on cattle detail admin.
- [ ] Custom bulk admin actions (e.g., **mark as steer**) with filters and confirmation.

## Dashboard
- [ ] Wire up **pregnant cows count** from breeding records.
- [ ] Add more robust **filters** for dashboard data (date ranges, owner filter, etc.).

## Breeding / Bulls
- [ ] Improve **bull pen list**:
  - [ ] Link bulls to their profile instead of generic cattle profile.
  - [ ] Remove/edit buttons that don’t match behavior.
- [ ] **Turnout group polish**: add open-gate emoji link, refine list view.

## General
- [ ] Add **audit log rollback** UI polish (restricted to dev/superuser).
- [ ] Track & highlight **inactive paddocks/pastures** across views (not just forms).

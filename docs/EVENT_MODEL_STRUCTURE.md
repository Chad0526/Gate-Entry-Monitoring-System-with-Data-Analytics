# Event Model Structure

## Staff-only and audit

- **AttendanceLog** has `recorded_by` (FK to User) so you can see which staff/guard recorded each scan, and `voided` / `voided_at` / `voided_by` for corrections. See **STAFF_ONLY_AND_DATA_CORRECTION.md**.

---

## Database fields (Event)

| Field | Type | Description |
|-------|------|-------------|
| **category** | FK → EventCategory | Event category |
| **name** | CharField(255), unique | Event name |
| **uid** | PositiveIntegerField, unique, null/blank OK | Auto-generated if blank |
| **description** | RichTextUploadingField | HTML description |
| **job_category** | FK → JobCategory | Job/career category |
| **venue** | CharField(255) | Venue name |
| **start_date** | DateField | Event start date |
| **end_date** | DateField | Event end date |
| **location** | LocationField (Mapbox) | Map location |
| **points** | PositiveIntegerField | Points for participation |
| **maximum_attende** | PositiveIntegerField | Capacity |
| **attendance_mode** | CharField | **OPEN** (student QR) or **SECURE** (token QR) |
| **status** | CharField | draft / scheduled / active / completed / cancelled / archived |
| created_user, updated_user | FK → User | Audit |
| **created_date** | **DateTimeField**(auto_now_add=True) | Audit |
| **updated_date** | **DateTimeField**(auto_now=True) | Audit (updates on every save) |

## Status (unified; no separate scheduled_status)

- **draft** — Not scheduled yet  
- **scheduled** — Scheduled  
- **active** — Currently running (used for gate/attendance)  
- **completed** — Ended  
- **cancelled** — Cancelled  
- **archived** — Archived / deleted  

## Related models

- **EventImage** — OneToOne with Event (one image per event). Editable on create and **edit**.
- **EventAgenda** — **Multiple rows per event** (ForeignKey). Create: one row in multi-form; **Edit: inline formset** (add/remove sessions).

## Create Event form sections (UI)

Create and Edit use a sectioned layout:

**Create:**  
1. Basic information, 2. Schedule & venue, 3. Attendance & capacity, 4. Status, 5. Event image, 6. Agenda (one row).  
Uses multi-form: `form.event`, `form.event_image`, `form.event_agenda`.

**Edit:**  
1. Basic information, 2. Schedule & venue, 3. Attendance & capacity, 4. Status, 5. **Event image** (change image), 6. **Agenda** (inline formset: multiple sessions, add/delete rows).  
Uses `form` (Event), `image_form` (EventImage), `agenda_formset` (EventAgendaFormSet).  

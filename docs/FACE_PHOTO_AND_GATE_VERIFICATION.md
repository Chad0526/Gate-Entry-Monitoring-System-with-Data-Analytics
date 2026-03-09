# Face Photo & Gate Verification (Capstone-Level)

This document describes the face photo and gate verification rules implemented for the CCB Gate Entry system (QR-only with photo verification).

---

## 1. Photo policy

- **One photo per student** (ID-style face photo).
- **Required** for registration; used for gate verification (anti-sharing).
- **Quality rules** (enforced server-side):
  - File type: valid image (validated with PIL).
  - Max size: 5 MB.
  - Min dimensions: 400×400 pixels (ensures clear display at gate).
- **Storage**: `media/students/<student_id>/face.jpg` (normalized path).
- **Processing**: Photos are converted to JPEG, resized to max width 800 px, quality 80 % (fast loading at gate).
- **Registrar/admin** can review and approve during account approval.

---

## 2. Account status workflow

1. **Registration** → Student account is created with **Pending** (inactive): `is_active=False`.
2. **Registrar review**:
   - Verify photo matches identity.
   - Activate account: set `is_active=True` (via Django admin or staff student edit).
   - Student can then use QR / scanning.
3. **Audit**: Use Django admin history and/or audit log for who approved/rejected and when.

---

## 3. Gate verification (QR scan → big card)

When a student’s QR is scanned at the gate:

- **Large photo** (180×180 px) is shown for quick visual verification.
- **ALLOWED** badge (green) when entry is granted.
- **Student ID**, **name**, **course/section**, **year level**.
- **Scan type**: IN or OUT.
- **Timestamp** of the scan.

This supports **anti-sharing**: the guard can confirm the person at the gate matches the photo on file.

---

## 4. Technical notes

- **Backend validation**: `events/forms.py` – `validate_student_photo()` (size, type, min dimensions).
- **Compression**: `events/utils.py` – `compress_student_photo()` (JPEG, max 800 px, quality 80).
- **Upload path**: `events/models.py` – `student_photo_upload_to()` → `students/<student_id>/face.jpg`.
- **Registration**: `gate_analytics/views.py` – validates and compresses photo (file or base64) before saving.
- **Gate popup**: `templates/gate/gate_scan.html` – student popup shows photo, ALLOWED, course, IN/OUT, time.

---

## 5. Optional: audit log for approval/rejection

To record who approved or rejected a registration and when:

- Add fields to `Student` (or a separate `RegistrationAudit` model): `approved_by` (FK to User), `approved_at` (DateTime), `rejection_reason` (TextField, optional).
- In admin or in a custom “approve student” view, set these when activating or rejecting.
- Use this in reports and in your manuscript as the audit trail for the workflow.

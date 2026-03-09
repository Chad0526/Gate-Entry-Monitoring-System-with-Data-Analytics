# Event Attendance - Year Level Added to Course/Section Display

## Feature Added
Added year level to the Course/Section column in event attendance reports and exports, so it now shows "BST - A - 2" instead of just "BST - A".

## Changes Made

### 1. Event Attendance Report View
**File**: `gate/gate_views.py`
**Function**: `reports_event_attendance()`

Updated the logic that builds `course_section_display` to include year level:
- Builds course + section (e.g., "BST - A")
- Adds year level to the end (e.g., "BST - A - 2")
- Handles cases where only some fields are present
- Shows "—" only if all fields are empty

**Display Format**:
- Course + Section + Year: "BST - A - 2"
- Course + Section only: "BST - A"
- Year only: "Year 2"
- None: "—"

### 2. Event Attendance Template
**File**: `templates/gate/reports/event_attendance.html`

Updated the column header from "Course/Section" to "Course/Section/Year" to reflect the new data.

### 3. CSV Export
**File**: `gate/gate_views.py`
**Function**: `event_attendance_report_export_csv()`

- Added `get_course_section_year()` helper function
- Updated CSV header to include "Course/Section/Year"
- Added course/section/year column to each row

**CSV Columns** (updated):
1. Student ID
2. Name
3. **Course/Section/Year** (NEW)
4. Checked In
5. Checked Out
6. Recorded At

### 4. Excel Export
**File**: `gate/gate_views.py`
**Function**: `event_attendance_report_export_xlsx()`

- Added `get_course_section_year()` helper function
- Updated Excel header to include "Course/Section/Year"
- Added course/section/year column to each row
- Adjusted column numbers (c4, c5, c6 instead of c3, c4, c5)

**Excel Columns** (updated):
1. Student ID
2. Name
3. **Course/Section/Year** (NEW)
4. Checked In
5. Checked Out
6. Recorded At

### 5. PDF Export
**File**: `gate/gate_views.py`
**Function**: `event_attendance_report_export_pdf()`

- Added `get_course_section_year()` helper function
- Updated PDF table header to include "Course/Section/Year"
- Added course/section/year column to each row
- Adjusted column widths to fit the new column

**PDF Columns** (updated):
1. Student ID (1.0 inch)
2. Name (1.5 inch)
3. **Course/Section/Year** (1.2 inch) (NEW)
4. Checked In (1.2 inch)
5. Checked Out (1.2 inch)
6. Recorded At (1.2 inch)

## Helper Function
All export functions now use a shared logic pattern via `get_course_section_year()`:

```python
def get_course_section_year(student):
    """Build course/section/year display for export."""
    # 1. Get course + section
    course_section = (student.course_or_section or '').strip()
    if not course_section:
        parts = []
        if getattr(student, 'course', None):
            parts.append(student.get_course_display())
        if getattr(student, 'section', None):
            parts.append(student.section.strip())
        course_section = ' - '.join(parts)
    
    # 2. Add year level
    year_level = getattr(student, 'year_level', None) or ''
    if course_section and year_level:
        return f"{course_section} - {year_level}"
    elif course_section:
        return course_section
    elif year_level:
        return f"Year {year_level}"
    return '—'
```

## Display Examples

### Web View (Attendees Tab)
| Student | Course/Section/Year | Check-in | Check-out |
|---------|---------------------|----------|-----------|
| 20240014 Teresa May Villanueva | BST - A - 2 | Mar 08, 22:31 | Mar 09, 00:39 |
| 20240006 Liza Marie Torres | BST - A - 3 | Mar 08, 22:31 | Mar 09, 00:39 |

### CSV Export
```
Student ID,Name,Course/Section/Year,Checked In,Checked Out,Recorded At
20240014,Villanueva, Teresa May,BST - A - 2,'2/25/2026 9:39 PM,'2/25/2026 10:15 PM,'2/25/2026 9:39 PM
```

### Excel Export
Same structure as CSV but in Excel format with proper formatting.

### PDF Export
Same structure as CSV but in PDF table format with styling.

## Benefits
- ✅ More complete student information in reports
- ✅ Easier to identify which year level students attended
- ✅ Consistent display across web view and all export formats
- ✅ Useful when events target specific year levels
- ✅ Helps with attendance analysis by year level

## Testing Instructions

1. **Web View**:
   - Go to Reports → Event Attendance
   - Select an event
   - Click "Attendees" tab
   - Verify column header shows "Course/Section/Year"
   - Verify data shows format like "BST - A - 2"

2. **CSV Export**:
   - Click "Export CSV" button
   - Open the downloaded file
   - Verify "Course/Section/Year" column exists
   - Verify data includes year level

3. **Excel Export**:
   - Click "Export Excel" button
   - Open the downloaded file
   - Verify "Course/Section/Year" column exists
   - Verify data includes year level

4. **PDF Export**:
   - Click "Export PDF" button
   - Open the downloaded file
   - Verify "Course/Section/Year" column exists
   - Verify data includes year level

## Status
✅ **COMPLETE** - Year level now included in Course/Section display across all event attendance views and exports.

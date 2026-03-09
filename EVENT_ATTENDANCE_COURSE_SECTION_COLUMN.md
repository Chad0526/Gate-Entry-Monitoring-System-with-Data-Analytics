# Event Attendance Report - Course/Section Column

## Problem
The Event Attendance report's Attendees tab was showing dashes (—) in the Course/Section column even though students had course and section data in their profiles.

## Root Cause
The template was only checking the `course_or_section` field, which is a legacy field that might be empty. Students have their course and section stored in separate fields:
- `course` - The course code (BST, BSE, etc.)
- `section` - The section name
- `course_or_section` - Legacy combined field (often empty)

## Solution
Updated the backend to build the course/section display by:
1. First checking if `course_or_section` has a value
2. If empty, building it from `course` and `section` fields
3. Using `get_course_display()` to get the human-readable course name
4. Joining course and section with " - " separator
5. Showing "—" only if both fields are empty

## Changes Made

### File: `gate/gate_views.py`
**Function**: `reports_event_attendance()` (line ~5297)

Added processing logic after fetching attendees:
```python
# Process attendees and add formatted course/section
attendees_list = list(checkins[:200])
for att in attendees_list:
    # Build course_or_section display: use course_or_section if set, else derive from course + section
    s = att.student
    course_section = (s.course_or_section or '').strip()
    if not course_section:
        parts = []
        if getattr(s, 'course', None):
            parts.append(s.get_course_display() if hasattr(s, 'get_course_display') else s.course)
        if getattr(s, 'section', None) and (s.section or '').strip():
            parts.append((s.section or '').strip())
        course_section = ' - '.join(parts) if parts else '—'
    # Add as attribute for template access
    att.course_section_display = course_section
attendees = attendees_list
```

### File: `templates/gate/reports/event_attendance.html`
**Section**: Attendees tab table

Changed from:
```html
<td>{% if a.student.course_or_section %}{{ a.student.course_or_section }}{% else %}—{% endif %}</td>
```

To:
```html
<td>{{ a.course_section_display }}</td>
```

## Display Format
The Course/Section column now shows:
- **If `course_or_section` is set**: Uses that value directly
- **If empty, but `course` and `section` exist**: Shows "BST - A", "BSE - B", etc.
- **If only `course` exists**: Shows "BST", "BSE", etc.
- **If only `section` exists**: Shows "A", "B", etc.
- **If both are empty**: Shows "—"

## Testing Instructions

1. **Navigate to Event Attendance Report**:
   - Go to Reports → Event Attendance
   - Select an event (e.g., "Webinar")
   - Click on the "Attendees" tab

2. **Verify Course/Section Display**:
   - Each student should now show their course and section
   - Format should be like "BST - A", "BSE - B", etc.
   - No more dashes (—) for students who have course/section data

3. **Test Different Scenarios**:
   - Students with `course_or_section` set → Shows that value
   - Students with separate `course` and `section` → Shows "COURSE - SECTION"
   - Students with only `course` → Shows just the course
   - Students with neither → Shows "—"

## Benefits
- ✅ Course/Section column now displays actual student data
- ✅ Handles both legacy `course_or_section` field and separate `course`/`section` fields
- ✅ Consistent with how course/section is displayed in other reports
- ✅ Better data visibility for event attendance tracking

## Status
✅ **COMPLETE** - Course/Section column now properly displays student course and section information.

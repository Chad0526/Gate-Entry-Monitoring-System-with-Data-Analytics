# Event Audience Scope - Course + Section + Year Level Option

## Feature Added
Added a new audience scope option "By course + section + year level" to the Event model, allowing events to target students by all three criteria simultaneously.

## Changes Made

### File: `gate/models.py`
**Model**: `Event`

#### 1. Updated `AUDIENCE_SCOPE_CHOICES`
Added new choice:
```python
('course_section_year', 'By course + section + year level'),
```

The complete list now includes:
- All students
- By course
- By year level
- By course + year level
- By course + section
- **By course + section + year level** (NEW)
- Specific students (registration list)

#### 2. Updated Field Help Text
Updated help text for audience fields to reflect the new scope:
- `audience_course`: Now mentions "course+section+year"
- `audience_year_level`: Now mentions "course+section+year"
- `audience_section`: Now mentions "course+section+year"

#### 3. Updated `audience_matches_student()` Method
Added logic to match students when scope is `course_section_year`:
```python
if scope == 'course_section_year':
    return bool(target_course and target_section and target_year) and \
           student_course == target_course and \
           student_section == target_section and \
           student_year == target_year
```

This checks that:
- All three fields (course, section, year) are configured
- Student's course matches the target course
- Student's section matches the target section
- Student's year level matches the target year level

#### 4. Updated `audience_summary()` Method
Added display format for the new scope:
```python
if scope == 'course_section_year':
    return f'Course + Section + Year: {self.audience_course or "—"} / {self.audience_section or "—"} / {self.audience_year_level or "—"}'
```

### File: `gate/gate_views.py`
**Function**: `_event_audience_students_qs()`

Updated the queryset builder to include `course_section_year` in the filtering logic:
```python
if scope in ('course', 'course_year', 'course_section', 'course_section_year'):
    # Filter by course
    
if scope in ('year_level', 'course_year', 'course_section_year'):
    # Filter by year level
    
if scope in ('course_section', 'course_section_year'):
    # Filter by section
```

### File: `templates/events/edit_event.html`
**JavaScript**: `toggleAudienceFields()` function

Updated the field visibility logic to show all three fields when `course_section_year` is selected:
```javascript
var showCourse = (scope === 'course' || scope === 'course_year' || scope === 'course_section' || scope === 'course_section_year');
var showYear = (scope === 'year_level' || scope === 'course_year' || scope === 'course_section_year');
var showSection = (scope === 'course_section' || scope === 'course_section_year');
```

### File: `templates/events/create_event.html`
**JavaScript**: `toggleAudienceFields()` function

Applied the same field visibility logic as in edit_event.html to ensure consistency.

## How It Works

When an event is configured with audience scope "By course + section + year level":

1. **Admin/Faculty sets up the event**:
   - Selects "By course + section + year level" from the Audience scope dropdown
   - Three input fields appear:
     - **Audience course** (e.g., "BST")
     - **Audience section** (e.g., "A")
     - **Audience year level** (e.g., "2")
   - All three fields must be filled in

2. **Student scans QR code**:
   - System checks if student's course, section, AND year level all match
   - Only students with matching course="BST", section="A", year_level="2" can check in
   - Other students get "Not eligible for this event" message

3. **Event reports show**:
   - Audience summary: "Course + Section + Year: BST / A / 2"
   - Only eligible students appear in attendance lists

## UI Behavior

When you select "By course + section + year level" from the dropdown:
- ✅ **Audience course** field appears
- ✅ **Audience section** field appears
- ✅ **Audience year level** field appears
- All three fields are displayed side by side (4 columns each on desktop)

When you select other options:
- "By course" → Only course field shows
- "By year level" → Only year level field shows
- "By course + year level" → Course and year level fields show
- "By course + section" → Course and section fields show
- "All students" → No fields show
- "Specific students" → Info message shows

## Use Cases

This new scope is useful for:
- **Section-specific events**: Events for a specific section of a specific year (e.g., "BST-A 2nd Year Field Trip")
- **Granular targeting**: When you need to target exactly one section of one year level
- **Class activities**: Section-based activities that are year-specific
- **Lab sessions**: Lab groups organized by course, section, and year

## Example Scenarios

### Scenario 1: BST-A 2nd Year Field Trip
- Audience scope: By course + section + year level
- Course: BST
- Section: A
- Year level: 2
- **Result**: Only BST-A 2nd year students can attend

### Scenario 2: BSE-B 3rd Year Seminar
- Audience scope: By course + section + year level
- Course: BSE
- Section: B
- Year level: 3
- **Result**: Only BSE-B 3rd year students can attend

## Testing Instructions

1. **Create/Edit an Event**:
   - Go to Events → Add Event (or edit existing)
   - In "Audience scope" dropdown, select "By course + section + year level"
   - Verify that three fields appear:
     - Audience course
     - Audience section
     - Audience year level
   - Fill in:
     - Audience course: BST
     - Audience section: A
     - Audience year level: 2
   - Save the event

2. **Test Field Visibility**:
   - Change audience scope to different options
   - Verify correct fields show/hide for each option
   - Change back to "By course + section + year level"
   - Verify all three fields appear again

3. **Test Student Eligibility**:
   - Have a student with course=BST, section=A, year_level=2 scan the event QR
   - Should successfully check in
   - Have a student with different course/section/year scan
   - Should get "Not eligible for this event" error

4. **Verify Display**:
   - Event details page should show: "Course + Section + Year: BST / A / 2"
   - Event attendance report should only show eligible students

## Database Migration

No migration is needed because:
- The `audience_scope` field already has `max_length=30` (sufficient for the new value)
- All other fields (`audience_course`, `audience_section`, `audience_year_level`) already exist
- This is just adding a new choice to an existing CharField

## Benefits
- ✅ More granular event targeting
- ✅ Combines all three student classification criteria
- ✅ Useful for section-specific activities
- ✅ Maintains consistency with existing audience scope patterns
- ✅ No database changes required
- ✅ Dynamic form fields show/hide based on selection
- ✅ Works in both create and edit event forms

## Status
✅ **COMPLETE** - New audience scope "By course + section + year level" is now available with dynamic form field visibility.

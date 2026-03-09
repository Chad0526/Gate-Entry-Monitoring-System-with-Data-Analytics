# Event Form Validation Fix - Course + Section + Year Level

## Problem Found
When saving an event with audience scope "By course + section + year level", the form was clearing the audience_course, audience_section, and audience_year_level fields, causing them to be saved as empty strings. This is why the event detail view showed dashes (—) instead of the actual values.

## Root Cause
The `EventForm.clean()` method in `gate/forms.py` had validation logic that didn't include the new `course_section_year` scope. The form was:
1. Checking if fields were required (but not including `course_section_year`)
2. Clearing fields that weren't needed by the selected scope (but not preserving fields for `course_section_year`)

## Fix Applied

### File: `gate/forms.py`
**Method**: `EventForm.clean()`

Updated three sections to include `course_section_year`:

#### 1. Validation - Require course field
```python
# Before:
if scope in ('course', 'course_year', 'course_section') and not course:

# After:
if scope in ('course', 'course_year', 'course_section', 'course_section_year') and not course:
```

#### 2. Validation - Require year level field
```python
# Before:
if scope in ('year_level', 'course_year') and not year:

# After:
if scope in ('year_level', 'course_year', 'course_section_year') and not year:
```

#### 3. Validation - Require section field
```python
# Before:
if scope == 'course_section' and not section:

# After:
if scope in ('course_section', 'course_section_year') and not section:
```

#### 4. Field Preservation - Keep course field
```python
# Before:
if scope not in ('course', 'course_year', 'course_section'):

# After:
if scope not in ('course', 'course_year', 'course_section', 'course_section_year'):
```

#### 5. Field Preservation - Keep year level field
```python
# Before:
if scope not in ('year_level', 'course_year'):

# After:
if scope not in ('year_level', 'course_year', 'course_section_year'):
```

#### 6. Field Preservation - Keep section field
```python
# Before:
if scope != 'course_section':

# After:
if scope not in ('course_section', 'course_section_year'):
```

## What This Fixes
- ✅ Form now validates that all three fields are filled when scope is `course_section_year`
- ✅ Form now preserves the values instead of clearing them
- ✅ Event detail view will now show actual values instead of dashes
- ✅ Students can now properly check in based on course + section + year level criteria

## Next Steps
You need to re-edit your event and save it again:
1. Go to the event that's showing dashes
2. Click "Edit Event"
3. The fields should still have your values (if not, re-enter them)
4. Click "Update Event"
5. The form will now properly save the values
6. Event detail view will show: "Course + Section + Year: BST / A / 2" (or whatever you entered)

## Status
✅ **COMPLETE** - Form validation now properly handles the `course_section_year` scope.

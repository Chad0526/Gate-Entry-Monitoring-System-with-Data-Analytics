# Audience Display - Why It Shows Dashes

## What You're Seeing
In the event detail view, the audience shows:
```
Course + Section + Year: — / — / —
```

## Why This Happens
The event has been configured with audience scope "By course + section + year level", but the three required fields are empty:
- **Audience course**: Empty (showing —)
- **Audience section**: Empty (showing —)
- **Audience year level**: Empty (showing —)

## This is NOT a Bug
The system is working correctly. It's showing dashes (—) because those fields haven't been filled in yet. The `audience_summary()` method displays:
- The actual value if it exists
- A dash (—) if the field is empty

## How to Fix
You need to edit the event and fill in the three audience fields:

1. **Go to the event** you want to fix
2. **Click "Edit Event"** button
3. **Scroll to "Attendance & capacity" section**
4. **Verify "Audience scope"** is set to "By course + section + year level"
5. **Fill in the three fields**:
   - **Audience course**: Select BST or BSE
   - **Audience section**: Type the section (e.g., "A", "B")
   - **Audience year level**: Select 1, 2, 3, or 4
6. **Click "Update Event"**

## After Fixing
Once you save the event with the fields filled in, the audience will display like:
```
Course + Section + Year: BST / A / 2
```

## Example Configuration

### For BST-A 2nd Year Students:
- Audience scope: By course + section + year level
- Audience course: BST
- Audience section: A
- Audience year level: 2
- **Result**: "Course + Section + Year: BST / A / 2"

### For BSE-B 3rd Year Students:
- Audience scope: By course + section + year level
- Audience course: BSE
- Audience section: B
- Audience year level: 3
- **Result**: "Course + Section + Year: BSE / B / 3"

## Important Notes
- The dashes (—) are placeholders for empty fields
- This is the expected behavior when fields are not filled in
- The system will still work, but students won't be able to check in until you specify the audience criteria
- If you leave the fields empty, NO students will match the audience criteria (because the system requires all three fields to be filled when using this scope)

## Status
✅ System is working correctly - just needs the event to be edited with the proper audience values.

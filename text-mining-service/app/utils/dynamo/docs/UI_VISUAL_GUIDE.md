# 🎨 Interface Visual Guide - Bulk Upload Status Tracking

## Table view with states:

### Example 1: First Load (All Pending)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│  Bulk Upload Results - capdev_data_2024.xlsx                                                │
│  📊 Found 5 records                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────────┘

┌────┬────┬──────────────┬────────────┬─────────────────────┬─────────────────────────────────┐
│ ☐  │ ID │   Status     │ STAR Link  │      Indicator      │             Title               │
├────┼────┼──────────────┼────────────┼─────────────────────┼─────────────────────────────────┤
│ ☐  │ 1  │ 🕐 Pending   │     -      │ Cap. Sharing Dev.   │ Training on climate adaptation  │
│ ☐  │ 2  │ 🕐 Pending   │     -      │ Cap. Sharing Dev.   │ Field visit irrigation systems  │
│ ☐  │ 3  │ 🕐 Pending   │     -      │ Cap. Sharing Dev.   │ Workshop on soil management     │
│ ☐  │ 4  │ 🕐 Pending   │     -      │ Cap. Sharing Dev.   │ Training on data analysis       │
│ ☐  │ 5  │ 🕐 Pending   │     -      │ Cap. Sharing Dev.   │ Engagement with farmers         │
└────┴────┴──────────────┴────────────┴─────────────────────┴─────────────────────────────────┘

[Submit Selected to STAR]
```

### Example 2: After the first record upload (Mixed)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│  Bulk Upload Results - capdev_data_2024.xlsx                                                │
│  📊 Found 5 records                                                                         │
│  📋 Selected: 3 of 5 records                                                                │
└─────────────────────────────────────────────────────────────────────────────────────────────┘

┌────┬────┬──────────────┬───────────────────────┬─────────────────────┬──────────────────────┐
│ ☐  │ ID │   Status     │      STAR Link        │      Indicator      │        Title         │
├────┼────┼──────────────┼───────────────────────┼─────────────────────┼──────────────────────┤
│ ☐  │ 1  │ ✓ Complete   │ 🔗 View in STAR       │ Cap. Sharing Dev.   │ Training climate...  │
│ ☐  │ 2  │ ✗ Failed     │         -             │ Cap. Sharing Dev.   │ Field visit irrig... │
│ ☑  │ 3  │ 🕐 Pending   │         -             │ Cap. Sharing Dev.   │ Workshop on soil...  │
│ ☑  │ 4  │ 🕐 Pending   │         -             │ Cap. Sharing Dev.   │ Training on data...  │
│ ☑  │ 5  │ 🕐 Pending   │         -             │ Cap. Sharing Dev.   │ Engagement with...   │
└────┴────┴──────────────┴───────────────────────┴─────────────────────┴──────────────────────┘

[Submit Selected to STAR]  [Clear Selections]
```

### Example 3: Next Day - Same File Reloaded

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│  Bulk Upload Results - capdev_data_2024.xlsx                                                │
│  📊 Found 5 records                                                                         │
│  ✅ Loaded previous statuses from database                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────┘

┌────┬────┬──────────────┬───────────────────────┬─────────────────────┬──────────────────────┐
│ ☐  │ ID │   Status     │      STAR Link        │      Indicator      │        Title         │
├────┼────┼──────────────┼───────────────────────┼─────────────────────┼──────────────────────┤
│ ☐  │ 1  │ ✓ Complete   │ 🔗 View in STAR       │ Cap. Sharing Dev.   │ Training climate...  │
│ ☑  │ 2  │ ✗ Failed     │         -             │ Cap. Sharing Dev.   │ Field visit irrig... │
│ ☐  │ 3  │ ✓ Complete   │ 🔗 View in STAR       │ Cap. Sharing Dev.   │ Workshop on soil...  │
│ ☐  │ 4  │ ✓ Complete   │ 🔗 View in STAR       │ Cap. Sharing Dev.   │ Training on data...  │
│ ☐  │ 5  │ ✓ Complete   │ 🔗 View in STAR       │ Cap. Sharing Dev.   │ Engagement with...   │
└────┴────┴──────────────┴───────────────────────┴─────────────────────┴──────────────────────┘

💡 Tip: Record 2 failed previously. Review and resubmit if corrected.

[Submit Selected to STAR]  [Clear Selections]
```

---

## Status Badges

### Status Pending (Yellow)
```
┌─────────────┐
│ 🕐 Pending  │
└─────────────┘
Background: #FEF3C7 (light yellow)
Text: #92400E (dark brown)
Border: #F59E0B (yellow)
```

### Status Complete (Green)
```
┌──────────────┐
│ ✓ Complete   │
└──────────────┘
Background: #D1FAE5 (light green)
Text: #065F46 (dark green)
Border: #10B981 (green)
```

### Status Failed (Red)
```
┌─────────────┐
│ ✗ Failed    │
└─────────────┘
Background: #FEE2E2 (light red)
Text: #991B1B (dark red)
Border: #EF4444 (red)
```

---

## Links to STAR

### Active Link (Registration Complete)
```
🔗 View in STAR
Color: #1474AC (medium blue)
Hover: #173F6F (dark blue) + underline
```

### No Link (Registration Pending or Failed)
```
-
Color: #9CA3AF (gray)
```

---

## System Status Messages

### Loading Previous States
```
┌────────────────────────────────────────────────────────┐
│  ⏳ Loading previous statuses...                       │
└────────────────────────────────────────────────────────┘
```

### First Load (No Previous States)
```
┌────────────────────────────────────────────────────────┐
│  ✅ Processed successfully! ⏱️ 3.45s                   │
│  📊 Found 5 records                                    │
└────────────────────────────────────────────────────────┘
```

### Successful upload to STAR
```
┌────────────────────────────────────────────────────────┐
│  ✅ Successfully submitted 3 records to STAR!          │
└────────────────────────────────────────────────────────┘
```

### Upload Error
```
┌────────────────────────────────────────────────────────┐
│  ❌ Error submitting to STAR: Network timeout          │
└────────────────────────────────────────────────────────┘
```

---

## Complete Visual Flow

### Step 1: File Selection
```
┌──────────────────────────────────────────────────────┐
│  📁 Choose Document Source                           │
│                                                      │
│  ⚪ Upload New File                                  │
│  ⚫ Load from S3                                     │
│                                                      │
│  [Select File: capdev_data_2024.xlsx]                │
│                                                      │
│  [Process Document]                                  │
└──────────────────────────────────────────────────────┘
```

### Step 2: Processing
```
┌──────────────────────────────────────────────────────┐
│                                                      │
│              ⏳ Processing...                        │
│                                                      │
│        Sending document to the service...            │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### Step 3: Results Displayed
```
┌──────────────────────────────────────────────────────┐
│  ✅ Processed successfully! ⏱️ 2.87s                 │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  📊 Found 50 records                                 │
│                                                      │
│  [Table with records - all in Pending]               │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### Step 4: Selection and Upload
```
┌──────────────────────────────────────────────────────┐
│  📋 Selected: 10 of 50 records                       │
│                                                      │
│  ┌────┬────┬──────────────┐                          │
│  │ ☑  │ 1  │ 🕐 Pending   │                          │
│  │ ☑  │ 2  │ 🕐 Pending   │                          │
│  │ ...│ ...│ ...          │                          │
│  │ ☑  │ 10 │ 🕐 Pending   │                          │
│  │ ☐  │ 11 │ 🕐 Pending   │                          │
│  └────┴────┴──────────────┘                          │
│                                                      │
│  [Submit Selected to STAR]                           │
└──────────────────────────────────────────────────────┘
```

### Step 5: Upload Processing
```
┌──────────────────────────────────────────────────────┐
│                                                      │
│       ⏳ Submitting 10 records to STAR platform...   │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### Step 6: Updated Results
```
┌──────────────────────────────────────────────────────┐
│  ✅ Successfully submitted 10 records to STAR!       │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  📊 Found 50 records                                 │
│                                                      │
│  ┌────┬────┬──────────────┬─────────────────┐        │
│  │ ☐  │ 1  │ ✓ Complete   │ 🔗 View in STAR │        │
│  │ ☐  │ 2  │ ✓ Complete   │ 🔗 View in STAR │        │
│  │ ☐  │ 3  │ ✗ Failed     │       -         │        │
│  │ ...│ ...│ ...          │ ...             │        │
│  │ ☐  │ 11 │ 🕐 Pending   │       -         │        │
│  └────┴────┴──────────────┴─────────────────┘        │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## Responsiveness

The table adapts to different screen sizes:

### Desktop (> 1200px)
- All columns visible
- Horizontal scroll if there are many columns
- Side-by-side buttons

### Tablet (768px - 1200px)
- Main columns visible
- Horizontal scrolling to view more columns
- Stacked buttons if necessary

### Mobile (< 768px)
- Card view instead of table (future consideration)
- Critical columns visible (ID, Status, Title)
- Vertically stacked buttons

---

## Interactivity

### Hover over Status Badge
- Slight shadow effect
- Default cursor (not clickable)

### Hover over STAR Link
- Color changes to dark blue
- Underline appears
- Pointer cursor

### Hover over Checkbox
- More pronounced border
- Pointer cursor

### Multiple Record Selection
- Checkboxes maintain status
- Counter updates in real time
- “Submit” button is dynamically enabled/disabled

---

## Accessibility

### Screen Readers
- Badges have descriptive text
- Links include explanatory text
- Inputs have appropriate labels

### Keyboard Navigation
- Tab navigates between interactive elements
- Enter/Space activates checkboxes and buttons
- Outline visible in focus

### Color Contrast
- All badges comply with WCAG AA
- Text is legible on all backgrounds
- Links are clearly distinguishable
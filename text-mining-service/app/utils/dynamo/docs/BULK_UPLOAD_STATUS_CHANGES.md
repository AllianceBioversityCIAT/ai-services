# Changes Summary - Bulk Upload Status Tracking

## 📋 General Description

A complete status tracking system has been implemented for bulk upload records, allowing users to:

1. View the status of each record (Pending, Complete, Failed)
2. Access results directly in STAR from the interface
3. Continue work across multiple sessions without losing progress
4. Quickly identify which records need attention

---

## 🎯 Implemented Features

### 1. New Table Columns

The table now includes three additional columns at the beginning:

- **ID**: Unique record identifier (comes in the data, displayed but NOT sent to STAR)
- **Status**: Record status with visual badges
  - 🕐 **Pending** (yellow): Pending upload
  - ✓ **Complete** (green): Successfully uploaded
  - ✗ **Failed** (red): Failed to upload
- **STAR Link**: Direct link to the result in STAR (only visible if status is Complete)

### 2. DynamoDB Persistence

**Table**: `bulk_upload_records`

**Structure**:
```
- fileName (Primary Key): File name
- complete: ["record_1", "record_5", ...]
- failed: ["record_3", "record_8", ...]
- links: {
    "record_1": "https://...",
    "record_5": "https://..."
  }
- lastUpdated: "2026-02-05T17:32:59.470Z"
```

### 3. Flow Logic

#### First File Load
1. User uploads an Excel file
2. Records are processed → All have **Pending** status
3. A record is created in DynamoDB with the file name

#### Upload to STAR
1. User selects records and presses "Submit to STAR"
2. Records are sent to STAR
3. Response is processed:
   - **Success**: `results_created` with `error: false`
     - Status → **Complete**
     - Link to STAR result is saved
   - **Failure**: `results_errors` with `error: true`
     - Status → **Failed**
4. Table is automatically updated with new statuses
5. Statuses are saved in DynamoDB

#### Subsequent Load of Same File
1. User loads the same file the next day
2. DynamoDB is queried by file name
3. Previous statuses are loaded and displayed in the table
4. User can see what remains to upload or what failed

---

## 📝 Code Changes

### Global State Variables

```javascript
let currentFileName = null;
let recordStatuses = {}; 
// Structure: { recordId: { status: 'pending'|'complete'|'failed', link: '...' } }
```

### New Functions

#### `loadRecordStatusesFromDynamo(fileName)`
- Loads saved statuses from DynamoDB
- Returns structure: `{ complete: [], failed: [], links: {} }`
- Handles the case when no previous record exists

#### `saveRecordStatusToDynamo(fileName, recordId, status, link)`
- Saves the status of ONE record in DynamoDB
- Parameters:
  - `fileName`: File name
  - `recordId`: Record ID
  - `status`: "complete" or "failed"
  - `link`: URL of the result in STAR (optional)

#### `processSTARResponse(starResponse, submittedResults)`
- Processes STAR response after uploading records
- Identifies which records were successful and which failed
- Updates local `recordStatuses`
- Saves each status in DynamoDB

### Modified Functions

#### `processDocument(mode, file, s3Key)`
- Now saves the file name in `currentFileName`
- Extracts file name from both upload and S3

#### `formatResultForSTAR(result)`
- Now removes the `id` field before sending to STAR
- The `id` field is only used internally for tracking

#### `submitToSTAR(selectedResults)`
- Now processes responses individually
- Calls `processSTARResponse()` to update statuses
- Reloads the table to display updated statuses

#### `displayResults(rawResult, elapsed)`
- Now is `async`
- Loads previous statuses from DynamoDB when a file is loaded
- Initializes `recordStatuses` with saved data
- Assigns "pending" to records that don't have a saved status

#### `renderResultsTable(results)`
- Handles two new column types:
  - `type: 'status'`: Renders status badges
  - `type: 'link'`: Renders links to STAR
- Fields with `readonly: true` are displayed with gray background and are not editable

---

## 🎨 Added CSS Styles

### CSS Variables
```css
--status-pending: #F59E0B;
--status-complete: #10B981;
--status-failed: #EF4444;
```

### Status Classes
```css
.status-pending   /* Yellow badge for pending records */
.status-complete  /* Green badge for completed records */
.status-failed    /* Red badge for failed records */
.star-link        /* Style for STAR links */
```

---

## 🔌 Required Backend Endpoints

See file `BACKEND_ENDPOINTS_NEEDED.md` for complete details.

### Summary:

1. **GET** `/dynamo/bulk-upload-records/{fileName}`
   - Retrieves saved statuses for a file
   
2. **POST** `/dynamo/bulk-upload-records`
   - Updates the status of a record
   - Body: `{ fileName, recordId, status, link? }`

---

## 📊 Complete Flow Example

### Day 1 - Initial Upload

```
1. User uploads "capdev_data_2024.xlsx"
   → 50 records, all in "Pending"

2. User selects records 1-10 and uploads them
   → STAR responds:
     - Records 1-9: ✓ Complete
     - Record 10: ✗ Failed

3. Table is updated:
   - Records 1-9: Status "Complete" + Link to STAR
   - Record 10: Status "Failed"
   - Records 11-50: Status "Pending"

4. Statuses are saved in DynamoDB
```

### Day 2 - Continuation

```
1. User uploads the same "capdev_data_2024.xlsx"
   
2. System queries DynamoDB
   → Loads previous statuses

3. Table is displayed with:
   - Records 1-9: ✓ Complete (already uploaded)
   - Record 10: ✗ Failed (needs correction)
   - Records 11-50: 🕐 Pending (remain to upload)

4. User can:
   - Review record 10 to correct the error
   - Continue uploading records 11-50
   - View in STAR the already completed records
```

---

## ✅ System Advantages

1. **Continuity**: Work can be done across multiple sessions
2. **Traceability**: Know exactly which records have been uploaded
3. **Quick Access**: Direct links to results in STAR
4. **Error Identification**: Failed records are easily identifiable
5. **No Duplication**: Avoid uploading the same record twice

---

## 🚀 Next Steps

1. **Implement backend endpoints** according to specifications in `BACKEND_ENDPOINTS_NEEDED.md`
2. **Create DynamoDB table** `bulk_upload_records`
3. **Configure IAM permissions** for DynamoDB access
4. **Test the complete flow** end-to-end
5. **Consider adding**:
   - Filters to view only pending/failed records
   - Button for "Retry Failed Records"
   - Export report of failed records
   - Real-time statistics (X of Y completed)

---

## 📌 Important Notes

- The `id` field must be present in the data returned by the processing service
- The `id` is displayed in the table but **NOT** sent to STAR
- Statuses are linked by `title` when processing the STAR response
- If a record fails and is later uploaded successfully, its status changes from "Failed" to "Complete"
- Links to STAR are only visible for records with "Complete" status

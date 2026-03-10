# Implementation Guide - Bulk Upload Status Tracking

## 📋 Summary of Implemented Changes

### Backend (✅ COMPLETED)

1. **Pydantic Models** added:
   - `RecordStatusUpdate`: For updating record statuses
   - `BulkUploadRecord`: DynamoDB table data model

2. **DynamoDB Table**:
   - Name: `bulk_upload_records`
   - Primary Key: `fileName` (String)
   - Created automatically on server startup
   - Billing Mode: PAY_PER_REQUEST (on-demand)

3. **New Endpoints**:
   - `GET /dynamo/bulk-upload-records/{fileName}` - Retrieve saved statuses
   - `POST /dynamo/bulk-upload-records` - Update a record's status

### Frontend (✅ COMPLETED)

See previous documentation files for frontend details.

---

## 🚀 Quick Start Guide

### Prerequisites

1. **AWS Credentials configured**:
   ```bash
   export AWS_ACCESS_KEY_ID="your-access-key"
   export AWS_SECRET_ACCESS_KEY="your-secret-key"
   export AWS_DEFAULT_REGION="us-east-1"
   ```

   Or using AWS CLI:
   ```bash
   aws configure
   ```

2. **Python 3.8+** installed
3. **Dependencies installed**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 📝 Step by Step: Complete Setup

### Step 1: Create DynamoDB Table

**Option A: Automatic Creation (Recommended)**

The table is created automatically when you start the server for the first time:

```bash
cd /Users/danielagomezayalde/Documents/Github/CGIAR/ai-services/text-mining-service
python -m uvicorn app.mcp.client:app --reload
```

The server will verify if the table exists and create it if necessary.

**Option B: Manual Creation**

If you prefer to create the table manually with sample data:

```bash
python create_dynamodb_table.py
```

This script:
- Verifies if the table exists
- Asks if you want to create it
- Optionally adds sample data
- Displays table information

### Step 2: Start the Server

```bash
python -m uvicorn app.mcp.client:app --reload --port 8000
```

You should see:
```
✅ Table bulk_upload_records created successfully
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 3: Verify Endpoints

**Option A: Using Test Script (Recommended)**

```bash
python test_dynamodb_endpoints.py
```

This script runs complete tests of all endpoints:
- ✅ Create records with 'complete' status
- ✅ Create records with 'failed' status
- ✅ Add multiple records
- ✅ Retrieve saved statuses
- ✅ Update status from failed to complete
- ✅ Handle non-existent files (404)
- ✅ Reject invalid statuses (400)

**Option B: Manual Testing with cURL**

1. **Create a completed record:**
```bash
curl -X POST http://localhost:8000/dynamo/bulk-upload-records \
  -H "Content-Type: application/json" \
  -d '{
    "fileName": "capdev_2024.xlsx",
    "recordId": "record_1",
    "status": "complete",
    "link": "https://main-allianceindicatorstest.ciat.cgiar.org/result-detail/19603"
  }'
```

2. **Create a failed record:**
```bash
curl -X POST http://localhost:8000/dynamo/bulk-upload-records \
  -H "Content-Type: application/json" \
  -d '{
    "fileName": "capdev_2024.xlsx",
    "recordId": "record_2",
    "status": "failed"
  }'
```

3. **Retrieve statuses:**
```bash
curl http://localhost:8000/dynamo/bulk-upload-records/capdev_2024.xlsx
```

Expected response:
```json
{
  "fileName": "capdev_2024.xlsx",
  "complete": ["record_1"],
  "failed": ["record_2"],
  "links": {
    "record_1": "https://main-allianceindicatorstest.ciat.cgiar.org/result-detail/19603"
  },
  "lastUpdated": "2026-02-05T12:30:45.123456"
}
```

**Option C: Using Swagger UI**

Open in your browser:
```
http://localhost:8000/docs
```

Look for the **"Bulk Upload Status"** section and test the endpoints interactively.

### Step 4: Test Complete Interface

1. Open the bulk upload interface:
   ```
   http://localhost:8000/bulk-upload
   ```

2. Upload an Excel file with CapDev data

3. After processing, you'll see the table with columns:
   - ID
   - Status (🕐 Pending by default)
   - STAR Link (empty at start)

4. Select records and press "Submit to STAR"

5. Statuses will automatically update to:
   - ✓ Complete (with link to STAR)
   - ✗ Failed (no link)

6. Reload the same file another day → Statuses will load from DynamoDB

---

## 🔍 Verifying the Table in AWS Console

1. Go to AWS console: https://console.aws.amazon.com/dynamodb
2. Select your region (us-east-1 by default)
3. Look for the `bulk_upload_records` table
4. Click "Explore table items" to see the data

---

## 🐛 Troubleshooting

### Error: "Unable to locate credentials"

**Problem**: AWS credentials not configured

**Solution**:
```bash
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_DEFAULT_REGION="us-east-1"
```

Or:
```bash
aws configure
```

### Error: "Table already exists"

**Problem**: Attempting to create a table that already exists

**Solution**: This is normal. The code automatically detects if the table exists and doesn't try to recreate it.

### Error: "Could not connect to the endpoint URL"

**Problem**: Incorrect region or DynamoDB unavailable

**Solution**:
1. Verify your region is correct in `config_util.py`
2. Verify you have internet connection
3. Verify DynamoDB is available in your region

### Error: 404 when retrieving statuses

**Problem**: File doesn't exist in the database

**Solution**: This is expected if the file hasn't been processed before. The frontend handles this case by showing all records as "Pending".

### Statuses are not being saved

**Problem**: Insufficient IAM permissions

**Solution**:
1. Verify your user/role has DynamoDB permissions:
   - `dynamodb:GetItem`
   - `dynamodb:PutItem`
   - `dynamodb:CreateTable` (only for initial creation)

2. Minimum IAM policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:CreateTable",
        "dynamodb:DescribeTable",
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:*:table/bulk_upload_records"
    }
  ]
}
```

---

## 📊 Data Structure in DynamoDB

### Item in the table:

```json
{
  "fileName": "capdev_2024.xlsx",
  "complete": ["record_1", "record_3", "record_5"],
  "failed": ["record_2", "record_4"],
  "links": {
    "record_1": "https://main-allianceindicatorstest.ciat.cgiar.org/result-detail/19603",
    "record_3": "https://main-allianceindicatorstest.ciat.cgiar.org/result-detail/19605",
    "record_5": "https://main-allianceindicatorstest.ciat.cgiar.org/result-detail/19607"
  },
  "lastUpdated": "2026-02-05T17:32:59.470Z"
}
```

---

## 📈 Metrics and Monitoring

### View metrics in AWS CloudWatch:

1. Go to CloudWatch in the AWS console
2. Select "Metrics"
3. Look for "DynamoDB" → `bulk_upload_records`
4. Important metrics:
   - `ConsumedReadCapacityUnits`
   - `ConsumedWriteCapacityUnits`
   - `UserErrors`
   - `SystemErrors`

### Application logs:

Logs include:
- ✅ Table creation/verification
- ✅ Status updates
- ❌ DynamoDB errors
- 📊 Read/write operations

---

## 🔄 Complete Data Flow

```
1. User uploads Excel file
   ↓
2. Backend processes → Each record gets an ID
   ↓
3. Frontend displays table with all records in "Pending"
   ↓
4. User selects records and presses "Submit to STAR"
   ↓
5. Frontend sends records to STAR API
   ↓
6. STAR responds with results_created and results_errors
   ↓
7. Frontend processes response:
   - Updates statuses locally
   - Calls POST /dynamo/bulk-upload-records for each record
   ↓
8. Backend saves statuses in DynamoDB
   ↓
9. Table updates showing new statuses
   ↓
10. User reloads page another day → Statuses load from DynamoDB
```

---

## ✅ Verification Checklist

Before considering the implementation complete, verify:

- [ ] Table `bulk_upload_records` exists in DynamoDB
- [ ] GET endpoint returns 404 for non-existent files
- [ ] POST endpoint creates new records correctly
- [ ] POST endpoint updates existing records
- [ ] Statuses are preserved between sessions
- [ ] Links to STAR are saved correctly
- [ ] Failed records don't have links
- [ ] Changing from failed to complete updates correctly
- [ ] Frontend loads statuses from DynamoDB when loading file
- [ ] Status badges display correctly in the UI
- [ ] Links to STAR work and open in new tab

---

## 📚 Reference Files

- `BACKEND_ENDPOINTS_NEEDED.md` - Original endpoint specification
- `BULK_UPLOAD_STATUS_CHANGES.md` - Complete changes summary
- `ID_FIELD_REQUIREMENT.md` - ID field requirements
- `IMPLEMENTATION_CHECKLIST.md` - Complete checklist
- `UI_VISUAL_GUIDE.md` - Interface visual guide
- `test_dynamodb_endpoints.py` - Automated tests
- `create_dynamodb_table.py` - Table creation script

---

## 🎯 Next Steps

1. **Implement `id` field in mining service** (See `ID_FIELD_REQUIREMENT.md`)
2. **Deploy to production**
3. **Configure monitoring and alerts**
4. **Consider future improvements** (See `IMPLEMENTATION_CHECKLIST.md`)

---

## 💡 Production Tips

1. **DynamoDB Backup**: Enable Point-in-time recovery
2. **Monitoring**: Configure CloudWatch alarms
3. **Costs**: Monitor consumption with PAY_PER_REQUEST
4. **Security**: Use specific IAM roles for production
5. **Testing**: Run tests regularly in staging environment

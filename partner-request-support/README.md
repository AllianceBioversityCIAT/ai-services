# CGIAR Partner Request Support System

> AI-powered institutional matching platform for CGIAR partner validation and CLARISA database integration

**A comprehensive full-stack application** that intelligently matches partner institution requests against the CLARISA institutional database using advanced hybrid search combining AI embeddings, fuzzy matching, and multilingual support with automated web research fallback.

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Installation & Setup](#-installation--setup)
- [Frontend Application](#-frontend-application)
- [Backend API](#-backend-api)
- [Hybrid Search Algorithm](#-hybrid-search-algorithm)
- [Database Schema](#-database-schema)
- [Configuration](#-configuration)
- [Usage Examples](#-usage-examples)
- [Development](#-development)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)

---

## 🎯 Overview

The CGIAR Partner Request Support System is an enterprise-grade platform designed to streamline and automate the process of validating and matching partner institutions against the official CLARISA (CGIAR Platform for Big Data in Agriculture) institutional database.

### **What It Does**

- **Validates** partner institution requests from Excel files or API sources
- **Matches** institutions using AI-powered hybrid search (semantic embeddings + fuzzy string matching)
- **Researches** missing institutions via automated web search when no database match exists
- **Manages** the complete approval workflow (accept/reject partner requests)
- **Synchronizes** with the CLARISA API for real-time institutional data
- **Provides** a modern web interface for managing the entire process

### **Who It's For**

- CGIAR institutional review teams
- Partner validation coordinators
- Research administrators managing institutional partnerships
- Teams requiring accurate institutional matching and validation

---

## ✨ Key Features

### 🎨 **Frontend Capabilities**

- **Dual Processing Modes**
  - Excel file upload with template support
  - Direct API integration with CLARISA partner requests
  
- **Interactive Results Dashboard**
  - Color-coded match quality indicators (Excellent/Good/Fair/No Match)
  - Real-time statistics with animated cards
  - Search and filter capabilities
  - Expandable detail views for each partner
  
- **Comprehensive Match Insights**
  - CLARISA match details with detailed scoring breakdowns
  - Top 5 candidate institutions with comparative analysis
  - AI-generated web research reports in markdown format
  - Manual web search trigger for quality improvement
  
- **Workflow Management**
  - Accept/reject partner requests directly from the UI
  - Optional rejection justification notes
  - Real-time UI updates after actions
  - Sync alerts for database changes
  
- **Professional Design**
  - CGIAR institutional branding (Poppins font, official color palette)
  - Smooth animations with Framer Motion
  - Responsive layout for all screen sizes
  - Accessibility-focused interface

### 🔧 **Backend Capabilities**

- **Hybrid Search Engine**
  - AI embeddings using Amazon Bedrock Titan v2 (1024 dimensions)
  - Fuzzy string matching with RapidFuzz
  - Multi-factor scoring algorithm combining semantic and exact matching
  - Configurable weights and thresholds
  
- **Multilingual Support**
  - Automatic language detection (langdetect library)
  - AWS Translate integration for non-English queries
  - Dual-language search (original + translated)
  
- **Intelligent Caching**
  - Partner-name-based caching to handle duplicates
  - Automatic cache invalidation on database updates
  - Persistent cache in PostgreSQL
  
- **Incremental Synchronization**
  - Only processes new/modified CLARISA institutions
  - Optional deletion of obsolete entries
  - Batch processing for efficiency
  
- **Web Search Fallback**
  - Two-phase AI approach: information gathering + analysis
  - OpenAI GPT-4o-mini for cost-effective web research
  - AWS Bedrock Claude Sonnet 4.5 for institutional analysis
  - CGIAR institutional rules compliance validation
  - Source tracking and citation
  
- **RESTful API**
  - FastAPI framework with automatic OpenAPI documentation
  - CORS-enabled for frontend integration
  - Comprehensive error handling
  - Request/response validation with Pydantic

---

## 🏗️ Architecture

### **Technology Stack**

#### **Frontend**
- **Framework**: Next.js 16.1.6 (App Router)
- **Language**: TypeScript 5.9.3
- **Styling**: Tailwind CSS 4 with PostCSS
- **Animations**: Framer Motion 12.34.5
- **Icons**: Lucide React 0.576.0
- **HTTP Client**: Axios 1.13.6
- **Markdown**: react-markdown 10.1.0 with GitHub Flavored Markdown support
- **Runtime**: React 19.2.3

#### **Backend**
- **Framework**: FastAPI (Python 3.8+)
- **Server**: Uvicorn (ASGI)
- **AI/ML Services**:
  - Amazon Bedrock (Titan Embed Text v2, Claude Sonnet 4.5)
  - OpenAI API (GPT-4o-mini)
  - AWS Translate
- **Database**: Supabase (PostgreSQL 15 + pgvector)
- **String Matching**: RapidFuzz
- **Language Detection**: langdetect
- **Data Processing**: Pandas, NumPy
- **Excel**: openpyxl
- **AWS SDK**: Boto3

#### **Infrastructure**
- **Vector Database**: Supabase with pgvector extension
- **Storage**: AWS S3 (template files)
- **Cloud Services**: AWS (Bedrock, Translate, S3)
- **API Integration**: CLARISA REST API

### **System Architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js 16 + React 19)             │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  page.tsx (Main Orchestrator)                              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              ↓                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  Components  │  │ Custom Hooks │  │   Services   │           │
│  │  (11 total)  │  │  (6 total)   │  │   (2 total)  │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│         ↓                  ↓                  ↓                 │
│  LoginPage         useAuth          authService                 │
│  Header            usePartnerProc.  partnerService              │
│  UploadSection     useFileUpload                                │
│  StatsCards        useApiSync                                   │
│  PartnerTable      useModal                                     │
│  QualityBadge      useWebSearch                                 │
│  ...                                                            │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/REST (Axios)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend API (FastAPI)                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    API Endpoints                         │   │
│  │  /api/process-partners  /api/sync-clarisa-institutions   │   │
│  │  /api/manual-web-search /api/respond-partner-request     │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Hybrid    │  │     Web     │  │   CLARISA   │              │ 
│  │   Search    │  │   Search    │  │     API     │              │
│  │   Engine    │  │   Module    │  │  Integration│              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└────────────┬────────────────┬───────────────────────────────────┘
             │                │
             ▼                ▼
┌──────────────────┐  ┌──────────────────┐
│    Supabase      │  │   AWS Services   │
│   PostgreSQL     │  │   - Bedrock      │
│   + pgvector     │  │   - Translate    │
│                  │  │   - S3           │
│  ┌────────────┐  │  └──────────────────┘
│  │Institutions│  │
│  │   Table    │  │  ┌──────────────────┐
│  └────────────┘  │  │   OpenAI API     │
│  ┌────────────┐  │  │   - GPT-4o-mini  │
│  │   Cache    │  │  │   - Web Search   │
│  │   Table    │  │  └──────────────────┘
│  └────────────┘  │
└──────────────────┘
```

---

## 🚀 Quick Start

### **Prerequisites**

- **Python** 3.8 or higher
- **Node.js** 18 or higher (for frontend)
- **Supabase** account with a project created
- **AWS Account** with Bedrock access enabled
- **OpenAI API** key
- **CLARISA API** access credentials

### **Full Stack Setup (Recommended)**

```bash
# 1. Clone the repository
git clone <repository-url>
cd partner-request-support

# 2. Set up environment variables (see Configuration section)
cp .env.example .env
# Edit .env with your credentials

# 3. Backend setup
cd backend
python -m venv ../.venv
source ../.venv/bin/activate  # On Windows: ..\.venv\Scripts\activate
pip install -r requirements.txt

# 4. Initialize database
# Execute sql/create_clarisa_vector_table.sql in Supabase SQL Editor
# Execute sql/create_partner_cache_table.sql in Supabase SQL Editor

# 5. Populate CLARISA database
python src/populate_clarisa_db.py
# This takes 10-15 minutes to generate embeddings for all institutions

# 6. Start backend API
python api.py
# API runs on http://localhost:8000

# 7. Frontend setup (new terminal)
cd ../frontend
npm install
npm run dev
# Frontend runs on http://localhost:3000
```

### **Environment URLs**

**Backend API:**
- 🔧 **Development**: http://localhost:8000
- 🧪 **Test**: https://hw4qszwcz55trf2n4xg7ujef7y0tgtya.lambda-url.us-east-1.on.aws
- 🚀 **Production**: https://eff4b5tkftulww4nllaebunmri0cdwrf.lambda-url.us-east-1.on.aws

**Frontend Application:**
- 🔧 **Development**: http://localhost:3000
- 🧪 **Test**: https://d27ujrreorxaxf.cloudfront.net
- 🚀 **Production**: https://d27ujrreorxaxf.cloudfront.net

---

## 🎨 Frontend Application

### **Architecture & Design Patterns**

The frontend follows modern React best practices with a **modular, scalable architecture**:

#### **Component-Based Structure**
- **11 Specialized Components**: Each component handles a single responsibility
  - `LoginPage` - Authentication interface
  - `Header` - Application header with branding and user info
  - `AIDisclaimer` - AI usage disclaimer banner
  - `UploadSection` - Dual-mode upload interface (Excel/API)
  - `StatsCards` - Animated statistics dashboard
  - `ResultsSection` - Complete results orchestrator
  - `PartnerTable` - Results table container
  - `PartnerRow` - Individual partner row with actions
  - `QualityBadge` - Color-coded match quality indicator
  - `SyncAlert` - Database sync notifications
  - `ModalDialog` - Reusable modal component

#### **Custom Hooks Pattern**
- **6 Custom Hooks** for separation of concerns and reusability:
  - `useAuth` - Authentication state and login/logout logic
  - `usePartnerProcessing` - Partner processing orchestration
  - `useApiSync` - API partner request synchronization
  - `useFileUpload` - File upload state management
  - `useModal` - Modal state and control
  - `useWebSearch` - Manual web search execution

#### **Service Layer**
- **Centralized API Communication**:
  - `authService` - CLARISA authentication API
  - `partnerService` - Partner processing endpoints
- Clean separation between UI logic and API calls
- Consistent error handling and response formatting

#### **Type System**
- **Full TypeScript Coverage**:
  - `partner.types` - Partner and match-related interfaces
  - `api.types` - API request/response schemas
  - `auth.types` - Authentication types
- Type-safe props and state management
- IntelliSense support throughout

#### **Utility Helpers**
- `qualityHelpers` - Match quality classification and badge rendering
- `fileHelpers` - File validation and processing helpers

### **Key Features**

#### **Authentication**
- Split-screen login interface with CGIAR branding
- Email/password authentication via CLARISA API
- Password visibility toggle and comprehensive error handling
- Automatic session management

#### **Processing Modes**

**Excel Upload Mode:**
- Drag-and-drop file upload (`.xlsx`, `.xls`)
- Template download from S3
- Real-time file validation
- Option to create partner requests in CLARISA first

**API Request Mode:**
- Sync pending partner requests from CLARISA API
- Auto-refresh capability
- Displays request count and metadata

#### **Results Dashboard**

**Statistics Cards** (animated with Framer Motion):
- Total Partners Processed
- Successfully Matched
- Excellent Matches (≥85% confidence)
- Web Searches Performed

**Results Table**:
- Partner Name, Acronym, Country (with flag emoji)
- Match Quality badge (color-coded)
- Actions: CLARISA Match, Top Candidates, Web Search
- Accept/Reject buttons (for API requests)
- Search/filter capabilities

**Match Quality Indicators**:
- 🟢 **Excellent** (≥85%): High confidence, verified match
- 🟡 **Good** (70-84%): Strong match, recommended for review
- 🟠 **Fair** (60-69%): Moderate match, needs validation
- ⚪ **No Match** (<60%): No suitable match found

#### **Modal Interactions**

- **CLARISA Match Modal**: Complete institution details with score breakdown
- **Top Candidates Modal**: Ranked list of top 5 potential matches
- **Web Search Modal**: AI-generated institutional research in markdown
- **Accept/Reject Modals**: Confirmation dialogs with optional justification

#### **Design System**

**Color Palette:**
- `#7AB800` - CGIAR Green (Primary)
- `#0065BD` - CGIAR Blue (Secondary)
- `#FFC84F` - CGIAR Yellow (Warning)
- `#272F53` - CGIAR Navy (Dark text)
- `#F5F7FA` - Light Gray (Background)

**Typography:** Poppins font family (Google Fonts)

### **State Management**

- **React Hooks-Based**: No external state management library needed
- **Custom Hooks** encapsulate complex state logic
- **Service Layer** handles API state
- **Local Component State** for UI-specific concerns
- **Prop Drilling Minimization** through composition

---

## 🔧 Backend API

### **Core Endpoints**

#### **`POST /api/process-partners`**
Upload and process Excel file with partner requests
- **Form Data**: file, user_email, user_name, auth_token, create_requests
- **Returns**: JSON with partners array, statistics, cache info

#### **`POST /api/process-api-partners`**
Process partners from synced API requests
- **Body**: a bare JSON array of partner request IDs, e.g. `[5723, 5751]` (optional)
- **Default**: with no body, processes the 10 oldest pending requests
- **Returns**: Same as process-partners

#### **`GET /api/sync-partner-requests`**
Fetch pending partner requests from CLARISA API
- **Returns**: Array of partner request objects

#### **`POST /api/sync-clarisa-institutions`**
Manually trigger CLARISA database sync
- **Body**: delete_obsolete (boolean)
- **Returns**: Sync statistics (new_count, modified_count, deleted_count)

#### **`POST /api/respond-partner-request`**
Accept or reject a partner request in CLARISA
- **Body**: request_id, user_id, accept, auth_token, reject_justification (if reject)
- **Returns**: Success confirmation or error

#### **`POST /api/manual-web-search`**
Trigger manual web search for an institution
- **Body**: partner_name (required), country, website (optional)
- **Returns**: AI-generated institutional report in markdown
- **Cost**: ~$0.02-0.03 per search

#### **`GET /api/download-template`**
Download Excel template from S3

#### **`GET /health`**
Health check endpoint

### **API Documentation**

**Development (localhost):**
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

**Test Environment:**
- **Swagger UI**: https://hw4qszwcz55trf2n4xg7ujef7y0tgtya.lambda-url.us-east-1.on.aws/docs
- **ReDoc**: https://hw4qszwcz55trf2n4xg7ujef7y0tgtya.lambda-url.us-east-1.on.aws/redoc

**Production Environment:**
- **Swagger UI**: https://eff4b5tkftulww4nllaebunmri0cdwrf.lambda-url.us-east-1.on.aws/docs
- **ReDoc**: https://eff4b5tkftulww4nllaebunmri0cdwrf.lambda-url.us-east-1.on.aws/redoc

---

## 🔍 Hybrid Search Algorithm

### **Six-Step Process**

```
STEP 1: Generate Embeddings
  → Amazon Bedrock Titan Embed Text v2 (1024 dimensions)
  
STEP 2: Dual-Language Support
  → Detect language (langdetect)
  → Translate to English if needed (AWS Translate)
  → Generate embeddings for both versions
  
STEP 3: Vector Search (Top 5 Candidates)
  → Cosine similarity on embeddings
  → Combined score: 0.7×name + 0.3×acronym
  → Threshold: 0.2 (pgvector IVFFlat index)
  
STEP 4: String Normalization & Fuzzy Matching
  → Normalize: lowercase, remove accents
  → RapidFuzz ratio for name and acronym
  
STEP 5: Final Scoring & Ranking
  → final_score = 0.60×cosine + 0.30×fuzz_name + 0.10×fuzz_acronym
  → Select candidate with highest score
  
STEP 6: Quality Classification
  → Excellent: ≥0.85
  → Good: 0.70-0.84
  → Fair: 0.60-0.69
  → No Match: <0.60 → triggers web search
```

### **Configuration Parameters**

```python
THRESHOLD_EMBEDDINGS = 0.2   # Vector search threshold
THRESHOLD_FINAL = 0.6        # Minimum match score
NAME_WEIGHT = 0.7            # Name embedding weight
ACRONYM_WEIGHT = 0.3         # Acronym embedding weight
COSINE_WEIGHT = 0.60         # Semantic similarity weight
FUZZ_NAME_WEIGHT = 0.30      # Name fuzzy weight
FUZZ_ACRONYM_WEIGHT = 0.10   # Acronym fuzzy weight
```

### **Why Hybrid?**

**Vector Embeddings**: Excellent at semantic understanding, language-agnostic  
**Fuzzy Matching**: Precise on exact character matches, handles typos  
**Combined**: Achieves >90% accuracy by leveraging strengths of both

---

## 🗄️ Database Schema

### **Table: `clarisa_institutions_v2`**

Stores all CLARISA institutions with pre-computed vector embeddings.

```sql
CREATE TABLE clarisa_institutions_v2 (
    id SERIAL PRIMARY KEY,
    clarisa_id INTEGER UNIQUE NOT NULL,
    name TEXT NOT NULL,
    acronym TEXT,
    website TEXT,
    countries TEXT[],
    institution_type TEXT,
    name_embedding vector(1024),
    acronym_embedding vector(1024),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Vector indexes (IVFFlat for approximate nearest neighbor search)
CREATE INDEX idx_name_embedding ON clarisa_institutions_v2 
    USING ivfflat (name_embedding vector_cosine_ops) WITH (lists = 100);
```

**Typical Row Count:** ~3,000-5,000 institutions

### **Table: `partner_request_cache_prod`**

Caches processing results to avoid redundant searches.

```sql
CREATE TABLE partner_request_cache_prod (
    request_id BIGINT PRIMARY KEY,
    partner_name TEXT NOT NULL,
    match_found BOOLEAN,
    match_quality TEXT,
    clarisa_match JSONB,
    top_candidates JSONB,
    web_search JSONB,
    api_data JSONB,
    processed_at TIMESTAMP DEFAULT NOW()
);
```

**Cache Strategy:**
- Caches by partner_name (lowercase normalized)
- Handles duplicates with same name but different IDs
- Invalidates automatically when CLARISA database updates

### **RPC Functions**

- `search_institution_by_name()` - Vector search by name embedding
- `search_institution_combined()` - Combined name + acronym search with weights

---

## ⚙️ Configuration

### **Environment Variables**

Create `.env` in `backend/` directory:

```bash
# CLARISA API
CLARISA_API_URL=clarisa-api-url
CLARISA_PARTNER_REQUESTS_URL=clarisa-partner-requests-url
CLARISA_CREATE_URL=clarisa-create-url
CLARISA_RESPOND_URL=clarisa-respond-url
CLARISA_COUNTRIES_URL=clarisa-countries-url
CLARISA_INSTITUTION_TYPES_URL=clarisa-institution-types-url

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key

# AWS (Bedrock and Translate)
AWS_ACCESS_KEY_ID_BR=AKIA...
AWS_SECRET_ACCESS_KEY_BR=your-secret-key
AWS_REGION=us-east-1

# OpenAI
OPENAI_API_KEY=sk-proj-...

# S3 (Template Storage)
S3_TEMPLATE_BUCKET=cgiar-partner-templates
S3_TEMPLATE_KEY=partner_request_template.xlsx

# CORS (Frontend URLs)
# Development, Test, and Production frontend URLs (comma-separated)
CORS_ORIGINS=http://localhost:3000,https://d27ujrreorxaxf.cloudfront.net
```

### **Frontend Configuration**

Create `.env.local` in `frontend/`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Test:**
```bash
NEXT_PUBLIC_API_URL=https://hw4qszwcz55trf2n4xg7ujef7y0tgtya.lambda-url.us-east-1.on.aws
```

**Production:**
```bash
NEXT_PUBLIC_API_URL=https://eff4b5tkftulww4nllaebunmri0cdwrf.lambda-url.us-east-1.on.aws
```

---

## 📝 Usage Examples

### **Excel File Processing**

```python
import requests

# Choose your environment:
# Dev: "http://localhost:8000"
# Test: "https://hw4qszwcz55trf2n4xg7ujef7y0tgtya.lambda-url.us-east-1.on.aws"
# Prod: "https://eff4b5tkftulww4nllaebunmri0cdwrf.lambda-url.us-east-1.on.aws"
url = "http://localhost:8000/api/process-partners"
with open("partners.xlsx", "rb") as f:
    files = {"file": f}
    data = {
        "user_email": "user@cgiar.org",
        "user_name": "John Doe",
        "auth_token": "token",
        "create_requests": "false"
    }
    response = requests.post(url, files=files, data=data)
    results = response.json()
```

### **Manual Search**

```python
from backend.src.mapping_clarisa_comparison import hybrid_search_institution

result = hybrid_search_institution(
    partner_name="Wageningen University",
    acronym="WUR",
    country="Netherlands"
)

print(f"Match: {result['name']}")
print(f"Score: {result['final_score']:.2f}")
print(f"Quality: {result['match_quality']}")
```

### **Web Search**

```python
from backend.src.web_search import search_institution_info

report = search_institution_info(
    name="Stanford University",
    country="United States",
    website="https://www.stanford.edu"
)
```

---

## 💻 Development

### **Project Structure**

```
partner-request-support/
├── frontend/
│   ├── app/
│   │   ├── page.tsx              # Main application (orchestrator)
│   │   ├── layout.tsx            # Root layout
│   │   ├── globals.css           # Global styles
│   │   │
│   │   ├── components/           # UI Components
│   │   │   ├── LoginPage.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── AIDisclaimer.tsx
│   │   │   ├── UploadSection.tsx
│   │   │   ├── StatsCards.tsx
│   │   │   ├── ResultsSection.tsx
│   │   │   ├── PartnerTable.tsx
│   │   │   ├── PartnerRow.tsx
│   │   │   ├── QualityBadge.tsx
│   │   │   ├── SyncAlert.tsx
│   │   │   ├── ModalDialog.tsx
│   │   │   └── index.ts
│   │   │
│   │   ├── hooks/                # Custom Hooks
│   │   │   ├── useAuth.ts
│   │   │   ├── usePartnerProcessing.ts
│   │   │   ├── useApiSync.ts
│   │   │   ├── useFileUpload.ts
│   │   │   ├── useModal.ts
│   │   │   ├── useWebSearch.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── services/             # API Services
│   │   │   ├── authService.ts
│   │   │   ├── partnerService.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── types/                # TypeScript Types
│   │   │   ├── partner.types.ts
│   │   │   ├── api.types.ts
│   │   │   ├── auth.types.ts
│   │   │   └── index.ts
│   │   │
│   │   └── utils/                # Utility Helpers
│   │       ├── qualityHelpers.tsx
│   │       └── fileHelpers.ts
│   │
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   └── postcss.config.mjs
│
├── backend/
│   ├── api.py                    # FastAPI entry point
│   ├── main.py                   # CLI script
│   ├── requirements.txt
│   │
│   ├── src/
│   │   ├── __init__.py
│   │   ├── mapping_clarisa_comparison.py  # Hybrid search engine
│   │   ├── clarisa_api.py                 # CLARISA API client
│   │   ├── embeddings.py                  # Embedding generation
│   │   ├── supabase_client.py             # Database operations
│   │   ├── utils.py                       # Utilities
│   │   ├── web_search.py                  # Web search module
│   │   └── populate_clarisa_db.py         # DB population
│   │
│   ├── config/
│   │   └── config_util.py
│   │
│   ├── docs/
│   │   ├── CGIAR_INSTITUTION_RULES.md
│   │   ├── HOW THE SEARCH WORKS.md
│   │   └── QUICKSTART.md
│   │
│   ├── sql/
│   │   ├── create_clarisa_vector_table.sql
│   │   └── create_partner_cache_table.sql
│   │
│   ├── test/
│   │   ├── search_example.py
│   │   └── web_search_test.py
│   │
│   └── logger/
│       └── logger_util.py
│
├── .env
├── .gitignore
├── README.md
└── skills-lock.json
```

### **Frontend Architecture Principles**

**Component Organization:**
- **Single Responsibility**: Each component handles one specific UI concern
- **Composition Over Inheritance**: Complex UIs built from simple, reusable components
- **Props Interface**: TypeScript interfaces for all component props

**Custom Hooks Benefits:**
- **Logic Reusability**: Share stateful logic across components
- **Separation of Concerns**: UI components focus on rendering, hooks handle logic
- **Testability**: Hooks can be tested independently
- **Code Organization**: Complex state management extracted from components

**Service Layer Pattern:**
- **Centralized API Logic**: All HTTP requests in dedicated service files
- **Error Handling**: Consistent error formatting across the app
- **Type Safety**: Typed request/response with TypeScript
- **Easier Mocking**: Services can be easily mocked for testing

### **Development Commands**

```bash
# Backend with auto-reload
cd backend
uvicorn api:app --reload --host 0.0.0.0 --port 8000

# Frontend with development mode
cd frontend
npm run dev

# Frontend with Turbopack (faster)
npm run dev --turbo
```

### **Adding New Features**

#### **Frontend: New Component**
```bash
# 1. Create component file
touch frontend/app/components/NewComponent.tsx

# 2. Add to index.ts for centralized exports
echo "export * from './NewComponent';" >> frontend/app/components/index.ts

# 3. Import in page.tsx or other components
# import { NewComponent } from './components';
```

#### **Frontend: New Custom Hook**
```bash
# 1. Create hook file
touch frontend/app/hooks/useNewFeature.ts

# 2. Add to index.ts
echo "export * from './useNewFeature';" >> frontend/app/hooks/index.ts

# 3. Use in components
# import { useNewFeature } from './hooks';
```

#### **Frontend: New Service Method**
```typescript
// In frontend/app/services/partnerService.ts
async newMethod(params: Params): Promise<Response> {
  const response = await axios.post(`${getApiUrl()}/api/new-endpoint`, params);
  return response.data;
}
```

#### **Backend: New API Endpoint**
```python
# 1. Add route in api.py
@app.post("/api/new-endpoint")
async def new_endpoint(data: RequestModel):
    # Implementation
    return {"result": "..."}

# 2. Implement business logic in src/ modules
# 3. OpenAPI docs update automatically
# 4. Add corresponding method in frontend partnerService.ts
```

#### **Database Changes**
1. Write migration SQL script in `backend/sql/`
2. Test in Supabase SQL editor
3. Document schema changes in README
4. Update cache invalidation logic if needed

---

## 🐛 Troubleshooting

### **"relation clarisa_institutions_v2 does not exist"**
Execute SQL scripts in Supabase SQL Editor:
- `sql/create_clarisa_vector_table.sql`
- `sql/create_partner_cache_table.sql`

### **"embedding dimension mismatch"**
Ensure using Amazon Bedrock Titan Embed Text **v2** (1024 dimensions):
```python
model_id = "amazon.titan-embed-text-v2:0"  # Not v1!
```

### **"pgvector index error"**
Rebuild vector indexes in Supabase:
```sql
DROP INDEX IF EXISTS idx_name_embedding;
CREATE INDEX idx_name_embedding ON clarisa_institutions_v2 
    USING ivfflat (name_embedding vector_cosine_ops) WITH (lists = 100);
```

### **Slow embedding generation**
- Use `us-east-1` region
- Reduce batch size in `populate_clarisa_db.py`
- Check AWS service quotas

### **CORS errors**
Ensure backend has CORS enabled in `api.py` for your frontend URLs:
- Development: `http://localhost:3000`
- Test: `https://d27ujrreorxaxf.cloudfront.net`
- Production: `https://d27ujrreorxaxf.cloudfront.net`

Check the `CORS_ORIGINS` environment variable in your `.env` file.

### **Cache not invalidating**
Manually clear cache:
```sql
DELETE FROM partner_request_cache_prod;
```

---
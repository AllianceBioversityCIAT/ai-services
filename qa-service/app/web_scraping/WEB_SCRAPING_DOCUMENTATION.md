# 📚 Complete Web Scraping System Documentation

## 🎯 Executive Summary

The web scraping system for the PRMS QA service allows automatic extraction of content from multiple sources to enrich the LLM model context with documentary evidence. The system automatically detects the source type and applies the most appropriate extraction strategy.

### ✅ Status: Fully Implemented and Functional

**Implemented**: November 2025  
**Version**: 1.0  
**Main files**:
- `web_scraping.py` - Main scraping service
- `evidence_scraper.py` - Integration with PRMS QA

### 🎯 Main Features

- ✅ **6 supported source types**: CGSpace, DOI, SharePoint, web pages, direct PDFs, Excel
- ✅ **Intelligent content validation**: Detects authentication and error pages
- ✅ **Multi-format extraction**: PDF, XLSX, HTML
- ✅ **Automatic detection**: Identifies URL type and applies correct strategy
- ✅ **Robust error handling**: Continues processing even if some URLs fail
- ✅ **Complete logging**: Tracks entire process for debugging
- ✅ **LLM integration**: Formats content optimized for the model

---

## 🏗️ System Architecture

### Complete Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    INPUT: User/API                          │
│  - result_metadata (PRMS data with evidence)                │
│  - user_id (optional)                                       │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              EvidenceEnhancer.enhance_prms_context()        │
│  1. Validates and limits URLs (max_evidences = 5)           │
│  2. Calls WebScraperService for each URL                    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              WebScraperService.scrape_url()                 │
│                                                             │
│  Automatic URL type detection:                              │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ YouTube?     │  │ DOI?         │  │ CGSpace?     │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │ No              │ No              │ No            │
│         ▼                 ▼                 ▼               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ SharePoint?  │  │ Web Page     │  │ Unsupported  │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Processing by Type                         │
│                                                             │
│  CGSpace Handle:                                            │
│    1. Playwright: Navigate to page                          │
│    2. Search for "download" button                          │
│    3. Build PDF URL                                         │
│    4. Requests: Download PDF                                │
│    5. PyMuPDF: Extract text                                 │
│    6. If fails: Search DOI → Follow DOI                     │
│    7. If no DOI: Extract metadata from page                 │
│                                                             │
│  DOI Article:                                               │
│    1. Playwright: Navigate (cookie/modal handling)          │
│    2. BeautifulSoup: Parse HTML                             │
│    3. Search for abstract and sections                      │
│    4. Extract main content                                  │
│                                                             │
│  SharePoint/OneDrive:                                       │
│    1. Convert URL to direct download format                 │
│    2. Requests: Download file                               │
│    3. Detect format (.pdf, .xlsx)                           │
│    4. PyMuPDF or pandas: Extract text                       │
│                                                             │
│  Web Page:                                                  │
│    1. Playwright: Render page                               │
│    2. BeautifulSoup: Parse HTML                             │
│    3. Search for main content (<main>, <article>)           │
│    4. Clean navigation, ads, scripts                        │
│    5. Extract structured text                               │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────────┐
│                 Content Validation System                     │
│                                                               │
│  _validate_content():                                         │
│    1. Empty content? → is_valid = False                       │
│    2. Less than 100 chars? → is_valid = False                 │
│    3. Title contains "sign in", "login"? → is_valid = False.  │
│    4. Title contains "404", "error"? → is_valid = False       │
│    5. 3+ auth indicators in content? → is_valid = False       │
│                                                               │
│  Result:                                                      │
│    - is_valid: True/False                                     │
│    - validation_reason: 'valid', 'authentication_required',   │
│                        'error_page', 'empty_content', etc.    │
│    - validation_message: Detailed description                 │
│    - validation_warnings: List of warnings                    │
└───────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│         EvidenceEnhancer.format_evidence_for_prompt()       │
│                                                             │
│  1. Filter invalid evidence and errors                      │
│  2. Format valid content with headers                       │
│  3. Include warnings if they exist                          │
│  4. Add separators and metadata                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   OUTPUT: Enriched Context                  │
│                                                             │
│  {                                                          │
│    "evidence_contents": [...],  // Complete list            │
│    "formatted_context": "...",  // Text for LLM             │
│    "evidence_count": N,         // Valid                    │
│    "invalid_count": M,          // Invalid                  │
│    "error_count": K,            // Errors                   │
│    "total_attempted": T         // Total processed          │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
```

### Main Components

#### 1. **WebScraperService** (`web_scraping.py`)

**Responsibility**: Extract content from different URL types

**Main methods**:
- `scrape_url(url)` - Main method, detects type and delegates
- `_is_youtube_url(url)` - Detects YouTube URLs
- `_is_doi_url(url)` - Detects DOI URLs
- `_is_cgspace_handle(url)` - Detects CGSpace handles
- `_is_sharepoint_url(url)` - Detects SharePoint/OneDrive
- `_scrape_cgspace_handle(url)` - Processes CGSpace handles
- `_scrape_doi(url)` - Processes DOI articles
- `_scrape_sharepoint_file(url)` - Downloads SharePoint files
- `_scrape_web_page(url)` - Processes general web pages
- `_validate_content(content, title, url)` - Validates extracted content
- `_extract_pdf_text(path)` - Extracts text from PDFs
- `_extract_excel_text(path)` - Extracts text from Excel

**Response structure**:
```python
{
    "type": "cgspace_pdf" | "doi_article" | "sharepoint_pdf" | 
            "sharepoint_xlsx" | "web_page" | "cgspace_metadata" |
            "invalid_content" | "error" | "unsupported_format",
    "title": str,
    "content": str,
    "url": str,
    "file_path": str,  # Only for downloaded files
    "is_valid": bool,
    "validation_reason": str,
    "validation_message": str,
    "validation_warnings": list  # Optional
}
```

#### 2. **EvidenceEnhancer** (`evidence_scraper.py`)

**Responsibility**: Coordinate extraction of multiple evidences and format for LLM

**Main methods**:
- `enhance_prms_context()` - Main orchestration method
- `extract_evidence_content()` - Process list of URLs
- `format_evidence_for_prompt()` - Format for LLM
- `_extract_evidence_urls_from_metadata()` - Extract URLs from metadata

**Configurable parameters**:
- `max_evidences = 5` - Limit of evidences to process
- `max_content_length = 3000` - Maximum characters per evidence

---

## 🌐 Supported Sources

### 1. 📄 CGSpace Handles

**Detected URLs**:
- `https://hdl.handle.net/10568/174072`
- `https://cgspace.cgiar.org/handle/10568/XXXXX`
- `https://cgspace.cgiar.org/items/XXXXX`

**Extraction strategy**:
1. **First**: Try to download PDF if available
2. **If fails**: Look for DOI on page and follow it
3. **If no DOI**: Extract metadata from page (abstract, metadata)

**Result type**: `cgspace_pdf` or `cgspace_metadata`

**Example**:
```python
result = await scraper.scrape_url("https://hdl.handle.net/10568/174072")
# Downloads PDF, extracts full text with PyMuPDF
```

### 2. 🔗 DOI Articles

**Detected URLs**:
- `https://doi.org/10.XXXX/XXXXX`
- URLs containing `doi.org/`

**Extraction strategy**:
1. Navigate with Playwright (handles JavaScript)
2. Close cookie banners and modals automatically
3. Search for abstract with specific selectors
4. Extract article sections
5. Parse main content with BeautifulSoup

**Special features**:
- Automatic cookie handling (detects 10+ button patterns)
- Modal and ad closing
- Intelligent abstract and section extraction
- 30-second timeout for slow pages

**Result type**: `doi_article`

**Example**:
```python
result = await scraper.scrape_url("https://doi.org/10.1234/example")
# Extracts abstract, introduction, main sections
```

### 3. 📦 SharePoint / OneDrive / Google Drive

**Detected URLs**:
- `https://cgiar.sharepoint.com/:b:/s/...`
- `https://onedrive.live.com/...`
- `https://drive.google.com/...`
- `https://1drv.ms/...`

**Supported formats**:
- ✅ **PDF** (.pdf) - Fully supported
- ✅ **Excel** (.xlsx) - Fully supported
- ⚠️ Other formats - Returns `unsupported_format`

**Extraction strategy**:
1. Convert URL to direct download format (`?download=1`)
2. Download file with requests
3. Detect format by extension
4. Extract content by format:
   - PDF: PyMuPDF
   - Excel: pandas (all sheets)

**Result type**: `sharepoint_pdf`, `sharepoint_xlsx`, `unsupported_format`

**Limitations**:
- Only works with public shared links
- Private links require authentication (not currently supported)
- Links may have expiration dates

**Example**:
```python
result = await scraper.scrape_url("https://cgiar.sharepoint.com/:b:/s/.../file.pdf")
# Downloads and extracts text from shared PDF
```

### 4. 🌐 General Web Pages

**URLs**: Any URL not from previous categories

**Extraction strategy**:
1. Render with Playwright (handles JavaScript)
2. Wait 2 seconds for dynamic content
3. Parse HTML with BeautifulSoup
4. Remove: scripts, styles, nav, header, footer, aside, iframe
5. Search for main content in order:
   - `<main>`
   - `<article>`
   - `[role="main"]`
   - `.main-content`, `#main-content`
   - `.content`, `#content`
6. Extract text from: h1-h6, p, li, td, th
7. Clean excessive whitespace

**Result type**: `web_page`

**Example**:
```python
result = await scraper.scrape_url("https://www.cgiar.org/news/article/")
# Extracts main content, ignores navigation and footer
```

### 5. 🚫 YouTube (Not Supported)

**Detected URLs**:
- `https://youtube.com/...`
- `https://youtu.be/...`
- `https://m.youtube.com/...`

**Result type**: `unsupported_content`

**Reason**: Videos cannot be scraped for text content

---

## ✅ Content Validation System

### Problem Solved

The scraper now automatically detects invalid content that was previously reported as "successful":
- Authentication pages (login, Auth0, etc.)
- Error pages (404, 403, 500)
- Empty or insufficient content

### Validation Indicators

#### Authentication Indicators
```python
AUTH_INDICATORS = [
    'sign in', 'log in', 'login', 'authenticate', 'auth0',
    'access denied', 'unauthorized', 'forbidden',
    'authentication required', 'please log in',
    'iniciar sesión', 'autenticación requerida'
]
```

#### Error Indicators
```python
ERROR_INDICATORS = [
    '404', 'not found', 'page not found',
    '403', 'forbidden', '401', 'unauthorized',
    '500', 'internal server error', 'error occurred',
    'no encontrada', 'error del servidor',
    'problem providing the content', 'content you requested',
    'content not available', 'page unavailable',
    'support team', 'contact support'
]
```

### Validation Rules

1. **Empty content** → `is_valid = False`, `reason = 'empty_content'`
2. **Content < 100 characters** → `is_valid = False`, `reason = 'insufficient_content'`
3. **Title contains auth indicator** → `is_valid = False`, `reason = 'authentication_required'`
4. **Title contains error indicator** → `is_valid = False`, `reason = 'error_page'`
5. **Content < 500 chars + contains error** → `is_valid = False`, `reason = 'error_page'`
6. **3+ auth warnings in content** → `is_valid = False`, `reason = 'likely_auth_page'`

### Validation Result Types

#### ✅ Valid Content
```python
{
    "is_valid": True,
    "validation_reason": "valid",
    "validation_message": "Content appears valid",
    "validation_warnings": []  # May contain non-critical warnings
}
```

#### ❌ Authentication Required
```python
{
    "is_valid": False,
    "validation_reason": "authentication_required",
    "validation_message": "Page appears to be a login/authentication page (title contains \"sign in\")"
}
```

#### ❌ Error Page
```python
{
    "is_valid": False,
    "validation_reason": "error_page",
    "validation_message": "Page appears to be an error page (title contains \"404\")"
}
```

#### ❌ Empty Content
```python
{
    "is_valid": False,
    "validation_reason": "empty_content",
    "validation_message": "No content extracted from the page"
}
```

### Automatic Filtering in Evidence Scraper

The `EvidenceEnhancer` automatically:
1. **Filters invalid evidences** from LLM context
2. **Logs detailed warnings** in logs
3. **Provides statistics**: valid, invalid, errors

**Log examples**:
```
2025-11-25 12:34:22 - WARNING - ⚠️ Invalid content detected for https://filemanager.cgiar.org/
2025-11-25 12:34:22 - WARNING -    Reason: authentication_required
2025-11-25 12:34:22 - WARNING -    Message: Page appears to be a login/authentication page
2025-11-25 12:34:22 - INFO - 📊 Evidence processing complete:
2025-11-25 12:34:22 - INFO -    Valid: 2/3
2025-11-25 12:34:22 - WARNING -    Invalid content: 1
```

---

## 🛠️ Technologies Used

### Complete Technology Stack

| Technology | Version | Purpose | When Used |
|------------|---------|---------|-----------|
| **Playwright** | Latest | Browser automation, JavaScript rendering | Dynamic pages, CGSpace, DOI |
| **BeautifulSoup4** | 4.x | Intelligent HTML parsing | All web pages |
| **PyMuPDF** | Latest | PDF text extraction | CGSpace, SharePoint PDFs |
| **pandas** | Latest | Excel processing | SharePoint .xlsx |
| **Requests** | 2.x | HTTP file downloads | Direct PDFs, SharePoint |
| **lxml** | Latest | Fast HTML/XML parser | BeautifulSoup backend |

### Technology Comparison

#### Why Playwright and not Selenium?

| Feature | Playwright | Selenium |
|---------|------------|----------|
| Speed | ⚡ Faster | Slower |
| Modern API | ✅ Native async/await | ❌ Synchronous |
| Auto-waits | ✅ Built-in | ⚠️ Manual |
| Event handling | ✅ Event-driven | ⚠️ Polling |
| Modern support | ✅ Updated | ⚠️ Legacy |

#### Why PyMuPDF and not PyPDF2?

| Feature | PyMuPDF | PyPDF2 |
|---------|---------|--------|
| Speed | ⚡ Much faster | Slow |
| Complex layouts | ✅ Excellent | ⚠️ Limited |
| Metadata | ✅ Complete | ⚠️ Basic |
| Maintenance | ✅ Active | ⚠️ Less active |

### Intelligent Hybrid Combination

The system uses the most appropriate tool for each case:

```
CGSpace Handle:
  Playwright → Dynamic navigation
  Requests → Efficient PDF download
  PyMuPDF → Text extraction

DOI Article:
  Playwright → JavaScript rendering
  BeautifulSoup → Intelligent HTML parsing

SharePoint:
  Requests → Direct download (no browser)
  PyMuPDF/pandas → Extraction by format

Web Page:
  Playwright → Dynamic content
  BeautifulSoup → Cleanup and extraction
```

---

## 📖 Usage Guide

### Dependency Installation

```bash
# Install all dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium
```

### Basic Usage - WebScraperService

```python
import asyncio
from app.web_scraping.web_scraping import WebScraperService

async def main():
    # Initialize scraper
    scraper = WebScraperService(download_dir="./data/evidence_downloads")
    
    # Scraping a CGSpace handle
    result = await scraper.scrape_url("https://hdl.handle.net/10568/174072")
    
    print(f"Type: {result['type']}")
    print(f"Title: {result['title']}")
    print(f"Valid: {result['is_valid']}")
    print(f"Content (first 500 chars): {result['content'][:500]}...")
    
    # Scraping a web page
    result = await scraper.scrape_url("https://www.cgiar.org/news/")
    print(f"\nWeb page: {result['title']}")
    
    # Scraping DOI
    result = await scraper.scrape_url("https://doi.org/10.1234/example")
    print(f"\nDOI: {result['title']}")

asyncio.run(main())
```

### Advanced Usage - EvidenceEnhancer

```python
import asyncio
from app.web_scraping.evidence_scraper import EvidenceEnhancer

async def main():
    # Initialize enhancer
    enhancer = EvidenceEnhancer(download_dir="./data/evidence_downloads")
    
    # List of evidence URLs
    evidence_urls = [
        "https://hdl.handle.net/10568/174072",
        "https://doi.org/10.1234/example",
        "https://www.cgiar.org/article/",
        "https://cgiar.sharepoint.com/:b:/s/.../file.pdf"
    ]
    
    # PRMS metadata (optional)
    result_metadata = {
        "result_type_name": "Impact",
        "result_level_name": "Output",
        "result_name": "Test Result"
    }
    
    # Process evidences
    result = await enhancer.enhance_prms_context(
        result_metadata=result_metadata,
        evidence_urls=evidence_urls,
        max_evidences=5
    )
    
    # Results
    print(f"✅ Valid evidences: {result['evidence_count']}")
    print(f"⚠️ Invalid content: {result['invalid_count']}")
    print(f"❌ Errors: {result['error_count']}")
    print(f"📊 Total processed: {result['total_attempted']}")
    
    # Formatted context for LLM
    if result['formatted_context']:
        print(f"\n📝 LLM context ({len(result['formatted_context'])} chars):")
        print(result['formatted_context'][:500] + "...")
    
    # Details of each evidence
    for evidence in result['evidence_contents']:
        print(f"\n{evidence['type']}: {evidence['title']}")
        print(f"  Valid: {evidence.get('is_valid', False)}")
        if not evidence.get('is_valid'):
            print(f"  Error: {evidence.get('error', 'Unknown')}")

asyncio.run(main())
```

### Quick Helper Function

```python
from app.web_scraping.evidence_scraper import get_evidence_context

async def quick_example():
    # Get formatted context directly
    context = await get_evidence_context([
        "https://hdl.handle.net/10568/174072",
        "https://www.cgiar.org/news/"
    ])
    
    print(context)

asyncio.run(quick_example())
```

---

## ⚠️ Error Handling

### Multi-Level Error Handling Strategy

```python
# Level 1: WebScraperService.scrape_url()
try:
    result = await scraper.scrape_url(url)
except Exception as e:
    # Log error, return error dict
    return {
        "type": "error",
        "content": "",
        "error": str(e),
        "is_valid": False
    }

# Level 2: EvidenceEnhancer.extract_evidence_content()
for url in evidence_urls:
    try:
        result = await scraper.scrape_url(url)
        # Process result
    except Exception as e:
        # Add error to list, continue with next URL
        evidence_contents.append({
            "type": "error",
            "error": str(e),
            "is_valid": False
        })

# Level 3: EvidenceEnhancer.enhance_prms_context()
# Always returns result, never fails completely
# If all URLs fail, returns evidence_count = 0
```

### Error Types and Responses

#### 1. Network/Timeout Error
```python
{
    "type": "error",
    "title": "Network Error",
    "content": "",
    "url": "https://...",
    "error": "Timeout waiting for page to load",
    "is_valid": False,
    "validation_reason": "scraping_error"
}
```

#### 2. Invalid Content (Authentication)
```python
{
    "type": "invalid_content",
    "title": "Sign In with Auth0",
    "content": "",
    "url": "https://...",
    "is_valid": False,
    "validation_reason": "authentication_required",
    "validation_message": "Page appears to be a login/authentication page"
}
```

#### 3. Unsupported Format
```python
{
    "type": "unsupported_format",
    "title": "document.docx",
    "content": "",
    "url": "https://...",
    "file_path": "./downloads/document.docx",
    "is_valid": False,
    "validation_reason": "unsupported_format",
    "validation_message": "File format .docx is not yet supported"
}
```

#### 4. Failed Download (SharePoint)
```python
{
    "type": "sharepoint_error",
    "title": "Download Failed",
    "content": "",
    "url": "https://...",
    "is_valid": False,
    "validation_reason": "download_failed",
    "validation_message": "Failed to download from SharePoint (HTTP 403)"
}
```

### Complete Logging

All events are logged in `data/logs/app.log`:

```python
# Scraping start
logger.info(f"🔗 [{idx}/{total}] Scraping: {url}")

# Success
logger.info(f"✅ Successfully scraped: {title} ({type})")
logger.info(f"Content preview: {content[:200]}...")

# Invalid content
logger.warning(f"⚠️ Invalid content detected for {url}")
logger.warning(f"   Reason: {validation_reason}")
logger.warning(f"   Message: {validation_message}")

# Validation warnings
logger.warning(f"⚠️ Validation warnings for {url}:")
for warning in warnings:
    logger.warning(f"   - {warning}")

# Error
logger.error(f"❌ Error scraping {url}: {str(e)}")

# Final summary
logger.info(f"📊 Evidence processing complete:")
logger.info(f"   Valid: {valid}/{total}")
logger.warning(f"   Invalid content: {invalid}")
logger.error(f"   Errors: {errors}")
```

---

## ⚙️ Configuration and Customization

### Configurable Parameters in WebScraperService

```python
scraper = WebScraperService(
    download_dir="./custom/downloads"  # Directory for downloaded files
)

# Modify minimum content length
scraper.MIN_CONTENT_LENGTH = 200  # Default: 100

# Add custom indicators
scraper.AUTH_INDICATORS.extend([
    'custom auth phrase',
    'portal de acceso',
    'área privada'
])

scraper.ERROR_INDICATORS.extend([
    'custom error',
    'página no disponible',
    'servicio no disponible'
])
```

### Configurable Parameters in EvidenceEnhancer

```python
enhancer = EvidenceEnhancer(
    download_dir="./data/evidence_downloads"  # Directory for files
)

result = await enhancer.enhance_prms_context(
    result_metadata=metadata,
    evidence_urls=urls,
    max_evidences=5  # Maximum evidences to process (default: 5)
)

# In extract_evidence_content
evidence_contents = await enhancer.extract_evidence_content(
    evidence_urls=urls,
    max_content_length=3000  # Maximum characters per evidence (default: 3000)
)
```

### Timeouts and Waits

```python
# In _scrape_doi (DOI articles)
await page.goto(url, wait_until="domcontentloaded", timeout=30000)  # 30 seconds

# In _scrape_web_page (general pages)
await page.goto(url, wait_until="domcontentloaded")  # Default timeout
await page.wait_for_timeout(2000)  # Wait 2 seconds for dynamic content

# In _scrape_cgspace_handle (CGSpace)
download_link = await page.get_by_role("link", name="download").get_attribute("href", timeout=3000)
```

### Suggested Environment Variables

```bash
# .env
WEB_SCRAPING_DOWNLOAD_DIR=./data/evidence_downloads
WEB_SCRAPING_MAX_EVIDENCES=5
WEB_SCRAPING_MAX_CONTENT_LENGTH=3000
WEB_SCRAPING_MIN_CONTENT_LENGTH=100
WEB_SCRAPING_TIMEOUT_MS=30000
```

---

## 💡 Practical Examples

### Example 1: Process Evidence List

```python
import asyncio
from app.web_scraping.evidence_scraper import EvidenceEnhancer

async def process_evidence_list():
    enhancer = EvidenceEnhancer()
    
    urls = [
        "https://hdl.handle.net/10568/174072",  # CGSpace PDF
        "https://doi.org/10.1234/example",      # DOI Article
        "https://www.cgiar.org/news/",          # Web Page
        "https://filemanager.cgiar.org/",       # Requires auth (will be filtered)
    ]
    
    result = await enhancer.enhance_prms_context(
        result_metadata={},
        evidence_urls=urls
    )
    
    # Show statistics
    print(f"✅ Valid: {result['evidence_count']}")
    print(f"⚠️ Invalid: {result['invalid_count']}")
    print(f"❌ Errors: {result['error_count']}")
    
    # Show details of each evidence
    for ev in result['evidence_contents']:
        status = "✅" if ev.get('is_valid') else "❌"
        print(f"{status} {ev['type']}: {ev['title']}")
        if not ev.get('is_valid'):
            print(f"   Reason: {ev.get('error', ev.get('validation_reason'))}")

asyncio.run(process_evidence_list())
```

### Example 2: Check URL Validity Before Processing

```python
async def check_url_validity(url: str):
    scraper = WebScraperService()
    result = await scraper.scrape_url(url)
    
    if result.get('is_valid', True):
        print(f"✅ Valid URL: {result['title']}")
        print(f"   Type: {result['type']}")
        print(f"   Content: {len(result['content'])} characters")
        return True
    else:
        print(f"❌ Invalid URL: {url}")
        print(f"   Reason: {result['validation_reason']}")
        print(f"   Message: {result['validation_message']}")
        return False

# Usage
asyncio.run(check_url_validity("https://filemanager.cgiar.org/"))
```

### Example 3: Process Only Valid Evidences

```python
async def process_only_valid():
    scraper = WebScraperService()
    urls = [
        "https://hdl.handle.net/10568/174072",
        "https://filemanager.cgiar.org/",  # Invalid
        "https://www.cgiar.org/news/"
    ]
    
    valid_results = []
    
    for url in urls:
        result = await scraper.scrape_url(url)
        if result.get('is_valid', True):
            valid_results.append(result)
            print(f"✅ Processed: {result['title']}")
        else:
            print(f"⚠️ Skipped: {url} - {result['validation_message']}")
    
    print(f"\nTotal valid: {len(valid_results)}/{len(urls)}")
    return valid_results

asyncio.run(process_only_valid())
```

### Example 4: Use Context in an LLM Prompt

```python
async def create_enhanced_prompt():
    from app.utils.prompt.prompt import build_prompt
    
    # PRMS metadata
    metadata = {
        "result_type_name": "Impact",
        "result_level_name": "Output",
        "result_name": "Climate-smart agriculture adoption",
        "result_description": "Increased adoption of climate-smart practices"
    }
    
    # Evidence URLs
    evidence_urls = [
        "https://hdl.handle.net/10568/174072",
        "https://www.cgiar.org/research/climate-change/"
    ]
    
    # Get evidence context
    enhancer = EvidenceEnhancer()
    evidence_data = await enhancer.enhance_prms_context(
        result_metadata=metadata,
        evidence_urls=evidence_urls
    )
    
    # Build base prompt
    base_prompt = build_prompt(
        metadata['result_type_name'],
        metadata['result_level_name'],
        metadata
    )
    
    # Add evidence context
    if evidence_data['formatted_context']:
        enhanced_prompt = f"""{base_prompt}

{evidence_data['formatted_context']}

Based on the evidence provided above, please enhance your response with specific data, 
findings, and references from these sources. Ensure your response is well-grounded 
in the documented evidence.
"""
    else:
        enhanced_prompt = base_prompt
    
    print(f"Prompt length: {len(enhanced_prompt)} characters")
    print(f"Evidences used: {evidence_data['evidence_count']}")
    
    return enhanced_prompt

asyncio.run(create_enhanced_prompt())
```

### Example 5: Handling Different File Types

```python
async def handle_different_file_types():
    scraper = WebScraperService()
    
    files = {
        "CGSpace PDF": "https://hdl.handle.net/10568/174072",
        "SharePoint Excel": "https://cgiar.sharepoint.com/:x:/s/.../data.xlsx",
        "SharePoint PDF": "https://cgiar.sharepoint.com/:b:/s/.../doc.pdf",
        "DOI Article": "https://doi.org/10.1234/example"
    }
    
    for name, url in files.items():
        result = await scraper.scrape_url(url)
        print(f"\n{name}:")
        print(f"  Type: {result['type']}")
        print(f"  Valid: {result.get('is_valid', False)}")
        
        if result.get('file_path'):
            print(f"  File: {result['file_path']}")
        
        if result.get('is_valid'):
            print(f"  Content: {len(result['content'])} chars")
        else:
            print(f"  Error: {result.get('validation_message', result.get('error'))}")

asyncio.run(handle_different_file_types())
```

---

## 🐛 Troubleshooting

### Problem: "Download is starting" on SharePoint

**Cause**: SharePoint URL starts automatic download in Playwright

**Solution**: System now uses direct download with requests instead of Playwright
```python
# Automatically detected and handled
result = await scraper.scrape_url("https://cgiar.sharepoint.com/:b:/s/.../file.pdf")
# Uses _scrape_sharepoint_file() automatically
```

### Problem: Empty Content or "Sign In"

**Cause**: Page requires authentication

**Solution**: Validation system detects it automatically
```python
# Validation detects and filters automatically
result = await scraper.scrape_url("https://filemanager.cgiar.org/")
# result['is_valid'] = False
# result['validation_reason'] = 'authentication_required'
```

### Problem: Timeout on Slow Pages

**Solution**: Adjust timeout for DOI articles
```python
# In _scrape_doi, timeout is already increased to 30 seconds
await page.goto(url, wait_until="domcontentloaded", timeout=30000)
```

### Problem: Cookie Banners Block Content

**Solution**: System automatically closes cookie banners and modals
```python
# Automatically detects and closes 10+ cookie button patterns
# See _scrape_doi() for complete implementation
```

### Problem: Unsupported File Format

**Solution**: Check result type
```python
result = await scraper.scrape_url(url)
if result['type'] == 'unsupported_format':
    print(f"Unsupported format: {result['validation_message']}")
    # Consider exporting to PDF from original source
```

### Problem: Expired SharePoint Links

**Solution**: Links may have expiration dates
```python
result = await scraper.scrape_url(sharepoint_url)
if result['validation_reason'] == 'download_failed':
    print("Link may be expired or requires authentication")
    # Request a new public link from user
```

---

## 📊 Statistics and Performance

### Limits and Recommendations

- **Recommended max evidences**: 5 URLs per request
- **Max content length**: 3000 characters per evidence
- **Maximum timeout**: 30 seconds for DOI articles
- **Maximum file size**: No limit, but consider 50MB for production

---

## 📝 Final Notes

### Key Files

- **Main implementation**: `app/web_scraping/web_scraping.py`
- **QA integration**: `app/web_scraping/evidence_scraper.py`
- **Logs**: `data/logs/app.log`
- **Downloads**: `data/evidence_downloads/`

### Unique System Features

1. **Intelligent Automatic Detection**: No need to specify source type
2. **Multi-Level Validation**: Automatically detects and filters invalid content
3. **Exhaustive Logging**: Every step is documented for debugging
4. **Resilient Error Handling**: Never fails completely, always returns result
5. **LLM Optimized**: Output format designed for model context
6. **Extensible**: Easy to add new source types or validations

### Best Practices

1. **Always check `is_valid`** before using content
2. **Limit `max_evidences`** to avoid timeouts
3. **Use logs** to diagnose problems
4. **Provide user feedback** about invalid evidences
5. **Consider caching** for frequent URLs in production

### Known Limitations

- Only public SharePoint links work (no authentication)
- YouTube is not supported (video content)
- Some formats require conversion to PDF (Word, PowerPoint)
- Links may expire (especially SharePoint)
- Very heavy pages may take >10 seconds

---
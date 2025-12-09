import os
import re
import asyncio
import pymupdf
import requests
import pandas as pd
from typing import Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from app.utils.logger.logger_util import get_logger

logger = get_logger()


class WebScraperService:
    MIN_CONTENT_LENGTH = 100
    
    AUTH_INDICATORS = [
        'sign in', 'log in', 'login', 'authenticate', 'auth0',
        'access denied', 'unauthorized', 'forbidden',
        'authentication required', 'please log in',
        'iniciar sesión', 'autenticación requerida'
    ]
    
    ERROR_INDICATORS = [
        '404', 'not found', 'page not found',
        '403', 'forbidden', '401', 'unauthorized',
        '500', 'internal server error', 'error occurred',
        'no encontrada', 'error del servidor',
        'problem providing the content', 'content you requested',
        'content not available', 'page unavailable',
        'support team', 'contact support'
    ]
    

    def __init__(self, download_dir: Optional[str] = None):
        target_dir = download_dir or os.getenv("WEB_SCRAPING_DOWNLOAD_DIR", "/tmp/evidence_downloads")
        self.download_dir = self._ensure_download_dir(target_dir)


    def _ensure_download_dir(self, target_dir: str) -> str:
        """
        Ensures the download directory exists and is writable. Falls back to /tmp on read-only filesystems.
        """
        try:
            os.makedirs(target_dir, exist_ok=True)
            return target_dir
        except OSError as exc:
            fallback_dir = "/tmp/evidence_downloads"
            if target_dir != fallback_dir:
                logger.warning(f"⚠️ Cannot create download dir '{target_dir}' ({exc}), using '{fallback_dir}' instead")
                os.makedirs(fallback_dir, exist_ok=True)
                return fallback_dir
            raise
    

    async def scrape_url(self, url: str) -> Dict[str, str]:
        if self._is_youtube_url(url):
            return {
                "type": "unsupported_content",
                "title": "YouTube Video",
                "content": "",
                "url": url,
                "is_valid": False,
                "validation_reason": "unsupported_content_type",
                "validation_message": "YouTube videos cannot be scraped for text content"
            }
        elif self._is_doi_url(url):
            return await self._scrape_doi(url)
        elif self._is_cgspace_handle(url):
            return await self._scrape_cgspace_handle(url)
        elif self._is_sharepoint_url(url):
            return await self._scrape_sharepoint_file(url)
        else:
            return await self._scrape_web_page(url)
    

    def _is_cgspace_handle(self, url: str) -> bool:
        """Detects if the URL is a CGSpace handle"""
        return "hdl.handle.net" in url or "cgspace.cgiar.org/handle" in url or "cgspace.cgiar.org/items" in url
    

    def _is_doi_url(self, url: str) -> bool:
        """Detects if the URL is a DOI"""
        return "doi.org/" in url.lower()
    

    def _is_sharepoint_url(self, url: str) -> bool:
        """Detects if the URL is from SharePoint or another sharing service"""
        sharepoint_indicators = [
            'sharepoint.com',
            'onedrive.live.com',
            'drive.google.com',
            '1drv.ms'
        ]
        return any(indicator in url.lower() for indicator in sharepoint_indicators)
    

    def _is_youtube_url(self, url: str) -> bool:
        """Detects if the URL is from YouTube"""
        youtube_indicators = [
            'youtube.com',
            'youtu.be',
            'm.youtube.com'
        ]
        return any(indicator in url.lower() for indicator in youtube_indicators)
    

    def _validate_content(self, content: str, title: str, url: str) -> Dict[str, any]:
        """
        Validates if the extracted content is useful or if it is an error/authentication page.
        
        Returns:
            Dict with 'is_valid', 'reason', 'warnings'
        """
        warnings = []
        
        if not content or len(content.strip()) == 0:
            return {
                'is_valid': False,
                'reason': 'empty_content',
                'message': 'No content extracted from the page',
                'warnings': warnings
            }
        
        if len(content.strip()) < self.MIN_CONTENT_LENGTH:
            return {
                'is_valid': False,
                'reason': 'insufficient_content',
                'message': f'Content too short ({len(content.strip())} chars, minimum {self.MIN_CONTENT_LENGTH})',
                'warnings': warnings
            }
        
        content_lower = content.lower()
        title_lower = title.lower()
        
        for indicator in self.AUTH_INDICATORS:
            if indicator in title_lower:
                return {
                    'is_valid': False,
                    'reason': 'authentication_required',
                    'message': f'Page appears to be a login/authentication page (title contains "{indicator}")',
                    'warnings': warnings
                }
            
            if indicator in content_lower:
                warnings.append(f'Content contains authentication keyword: "{indicator}"')
        
        for indicator in self.ERROR_INDICATORS:
            if indicator in title_lower:
                return {
                    'is_valid': False,
                    'reason': 'error_page',
                    'message': f'Page appears to be an error page (title contains "{indicator}")',
                    'warnings': warnings
                }
            
            if indicator in content_lower:
                if len(content.strip()) < 500:
                    return {
                        'is_valid': False,
                        'reason': 'error_page',
                        'message': f'Page appears to be an error page (content contains "{indicator}")',
                        'warnings': warnings
                    }
                warnings.append(f'Content contains error keyword: "{indicator}"')
        
        if len(warnings) >= 3:
            return {
                'is_valid': False,
                'reason': 'likely_auth_page',
                'message': 'Multiple authentication indicators found in content',
                'warnings': warnings
            }
        
        return {
            'is_valid': True,
            'reason': 'valid',
            'message': 'Content appears valid',
            'warnings': warnings
        }
    

    async def _scrape_cgspace_handle(self, url: str) -> Dict[str, str]:
        """
        Extracts content from CGSpace handles.
        Strategy:
        1. Try to download the PDF file if available
        2. If there is no PDF, look for DOI and follow it
        3. If there is no DOI or the DOI is not valid, extract metadata from the page
        """
        logger.info(f"📄 Scraping CGSpace handle: {url}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process",
                    "--no-zygote",
                ],
            )
            page = await browser.new_page()
            
            await page.goto(url)
            title = await page.title()
            
            try:
                download_link = await page.get_by_role("link", name="download").get_attribute("href", timeout=3000)
                
                uuid = download_link.split("/")[2]
                real_url = f"https://cgspace.cgiar.org/server/api/core/bitstreams/{uuid}/content"
                
                r = requests.get(real_url)
                filename = os.path.join(self.download_dir, f"{uuid}.pdf")
                
                with open(filename, "wb") as f:
                    f.write(r.content)
                
                await browser.close()
                logger.info(f"✅ Downloaded PDF: {filename}")
                
                text = self._extract_pdf_text(filename)
                validation = self._validate_content(text, title, url)
                
                result = {
                    "type": "cgspace_pdf",
                    "title": title,
                    "content": text,
                    "url": url,
                    "file_path": filename,
                    "is_valid": validation['is_valid'],
                    "validation_reason": validation['reason'],
                    "validation_message": validation['message']
                }
                
                if validation['warnings']:
                    result['validation_warnings'] = validation['warnings']
                
                return result
                
            except Exception as e:
                logger.info(f"⚠️  No download link found, looking for DOI...")
                
                doi_url = None
                try:
                    doi_element = await page.query_selector('a[href*="doi.org"]')
                    if doi_element:
                        doi_url = await doi_element.get_attribute("href")
                        logger.info(f"✅ Found DOI: {doi_url}, following it...")
                except Exception:
                    pass
                
                if doi_url:
                    current_html = await page.content()
                    await browser.close()
                    
                    doi_result = await self._scrape_doi(doi_url)
                    
                    if doi_result['is_valid']:
                        return doi_result
                    
                    logger.info(f"⚠️  DOI content invalid, extracting from CGSpace page...")
                    return self._extract_cgspace_page_content(current_html, url, title)
                
                logger.info(f"⚠️  No DOI found, extracting from CGSpace page...")
                current_html = await page.content()
                await browser.close()
                return self._extract_cgspace_page_content(current_html, url, title)
    

    def _extract_cgspace_page_content(self, html_content: str, url: str, title: str) -> Dict[str, str]:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        text_parts = [f"Title: {title}", "=" * 60]
        
        for selector in ['div.abstract', 'div.description', 'div[class*="description"]', 'div[class*="abstract"]']:
            abstract = soup.select_one(selector)
            if abstract:
                text_parts.append("Abstract:")
                text_parts.append(abstract.get_text(strip=True))
                break
        
        metadata_items = soup.select('div.simple-item-view-metadata')
        for item in metadata_items:
            text = item.get_text(separator='\n', strip=True)
            if text:
                text_parts.append(text)
        
        content = '\n\n'.join(text_parts)
        validation = self._validate_content(content, title, url)
        
        result = {
            "type": "cgspace_metadata",
            "title": title,
            "content": content,
            "url": url,
            "is_valid": validation['is_valid'],
            "validation_reason": validation['reason'],
            "validation_message": validation['message']
        }
        
        if validation['warnings']:
            result['validation_warnings'] = validation['warnings']
        
        return result
    

    async def _scrape_doi(self, url: str) -> Dict[str, str]:
        logger.info(f"🔗 Scraping DOI: {url}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process",
                    "--no-zygote",
                ],
            )
            page = await browser.new_page()
            
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                try:
                    await page.wait_for_timeout(3000)
                    
                    cookie_buttons = [
                        'button:has-text("Accept all")',
                        'button:has-text("Accept all cookies")',
                        'button:has-text("Accept")',
                        'button:has-text("Aceptar")',
                        'button:has-text("I accept")',
                        'button[id*="accept"]',
                        'button[class*="accept"]',
                        'button[id*="cookie"]',
                        'a:has-text("Accept")',
                        '#onetrust-accept-btn-handler'
                    ]
                    
                    for selector in cookie_buttons:
                        try:
                            await page.click(selector, timeout=2000)
                            logger.info("✅ Closed cookie banner")
                            await page.wait_for_timeout(1000)
                            break
                        except:
                            continue

                    close_buttons = [
                        'button[aria-label="Close"]',
                        'button[aria-label="close"]',
                        'button.close',
                        '[class*="close-button"]',
                        '[class*="modal-close"]',
                        'button:has-text("Close")',
                        'button:has-text("×")',
                        'button:has-text("✕")'
                    ]
                    
                    for selector in close_buttons:
                        try:
                            await page.click(selector, timeout=1000)
                            logger.info("✅ Closed modal/ad")
                            await page.wait_for_timeout(500)
                        except:
                            continue
                            
                except:
                    pass
                
                title = await page.title()
                content_html = await page.content()
                await browser.close()
                
                soup = BeautifulSoup(content_html, 'html.parser')
                
                for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                    element.decompose()
                
                text_parts = []
                
                abstract_found = False
                abstract_selectors = [
                    ('id', 'abstract'),
                    ('id', 'abs0010'),
                    ('id', 'abspara'),
                    ('class', 'abstract'),
                    ('class', 'Abstract'),
                    ('class', 'section-abstract'),
                ]
                
                for attr, value in abstract_selectors:
                    if attr == 'id':
                        abstract = soup.find(id=value) or soup.find(['div', 'section'], id=value)
                    else:
                        abstract = soup.find(['div', 'section'], class_=lambda x: x and value.lower() in str(x).lower() if x else False)
                    
                    if abstract:
                        text_parts.append("Abstract:")
                        text_parts.append(abstract.get_text(separator='\n', strip=True))
                        abstract_found = True
                        break
                
                sections = soup.find_all(['section', 'div'], id=lambda x: x and ('sec' in str(x).lower() or 'section' in str(x).lower()) if x else False)
                if sections:
                    for section in sections:
                        section_title = section.find(['h2', 'h3', 'h4'])
                        if section_title:
                            text_parts.append(f"\n{section_title.get_text(strip=True)}")
                        
                        paragraphs = section.find_all('p')
                        for p in paragraphs:
                            text = p.get_text(strip=True)
                            if text and len(text) > 30:
                                text_parts.append(text)
                
                if len(text_parts) <= 1:
                    article = soup.find('article') or soup.find('main') or soup.find('div', class_=lambda x: x and 'content' in x.lower() if x else False)
                    if article:
                        paragraphs = article.find_all(['p', 'h1', 'h2', 'h3', 'h4'])
                        for p in paragraphs:
                            text = p.get_text(strip=True)
                            if text and len(text) > 30:
                                text_parts.append(text)
                
                if not text_parts:
                    text_parts.append(soup.get_text(separator='\n\n', strip=True))
                
                content = '\n\n'.join(text_parts)
                content = re.sub(r'\n{3,}', '\n\n', content)
                
                validation = self._validate_content(content, title, url)
                
                result = {
                    "type": "doi_article",
                    "title": title,
                    "content": content,
                    "url": url,
                    "is_valid": validation['is_valid'],
                    "validation_reason": validation['reason'],
                    "validation_message": validation['message']
                }
                
                if validation['warnings']:
                    result['validation_warnings'] = validation['warnings']
                
                await browser.close()
                return result
                
            except Exception as e:
                await browser.close()
                return {
                    "type": "doi_article",
                    "title": "Error",
                    "content": "",
                    "url": url,
                    "is_valid": False,
                    "validation_reason": "scraping_error",
                    "validation_message": f"Error accessing DOI: {str(e)}"
                }
    

    def _convert_sharepoint_to_download_url(self, url: str) -> str:
        """
        Converts a SharePoint/OneDrive URL to a direct download URL.
        
        SharePoint URLs usually look like:
        https://[tenant].sharepoint.com/:b:/s/[site]/[encoded_path]
        
        It can be converted adding ?download=1 at the end.
        """

        if 'download=' in url:
            return url
        
        separator = '&' if '?' in url else '?'
        return f"{url}{separator}download=1"
    

    async def _scrape_sharepoint_file(self, url: str) -> Dict[str, str]:
        """
        Downloads and extracts content from shared files in SharePoint/OneDrive.
        Uses direct download with requests.
        """
        logger.info(f"📦 Scraping SharePoint/shared file: {url}")
        
        download_url = self._convert_sharepoint_to_download_url(url)
        
        logger.info(f"🔄 Attempting direct download...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(download_url, headers=headers, allow_redirects=True, timeout=15)
        
        if response.status_code != 200:
            return {
                "type": "sharepoint_error",
                "title": "Download Failed",
                "content": "",
                "url": url,
                "is_valid": False,
                "validation_reason": "download_failed",
                "validation_message": f"Failed to download from SharePoint (HTTP {response.status_code})"
            }
        
        if len(response.content) < 100:
            return {
                "type": "sharepoint_error",
                "title": "Download Failed",
                "content": "",
                "url": url,
                "is_valid": False,
                "validation_reason": "download_failed",
                "validation_message": "Downloaded file is too small or empty (likely auth required)"
            }

        content_disposition = response.headers.get('content-disposition', '')
        if 'filename=' in content_disposition:
            filename = content_disposition.split('filename=')[1].strip('"\'')
        else:
            filename = f"sharepoint_file_{abs(hash(url))}.pdf"
        
        download_path = os.path.join(self.download_dir, filename)
        
        with open(download_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"✅ Download successful: {download_path}")

        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext == '.pdf':
            text = self._extract_pdf_text(download_path)
            file_type = "sharepoint_pdf"
        elif file_ext == '.xlsx':
            text = self._extract_excel_text(download_path)
            file_type = "sharepoint_xlsx"
        else:
            return {
                "type": "unsupported_format",
                "title": filename,
                "content": "",
                "url": url,
                "file_path": download_path,
                "is_valid": False,
                "validation_reason": "unsupported_format",
                "validation_message": f"File format {file_ext} is not yet supported"
            }
        
        validation = self._validate_content(text, filename, url)
        
        result = {
            "type": file_type,
            "title": filename,
            "content": text,
            "url": url,
            "file_path": download_path,
            "is_valid": validation['is_valid'],
            "validation_reason": validation['reason'],
            "validation_message": validation['message']
        }
        
        if validation['warnings']:
            result['validation_warnings'] = validation['warnings']
        
        return result

    
    async def _scrape_web_page(self, url: str) -> Dict[str, str]:
        """
        Extract content from a general web page using Playwright + BeautifulSoup.
        Intelligently extracts the main content ignoring navigation, ads, etc.
        """
        logger.info(f"🌐 Scraping web page: {url}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process",
                    "--no-zygote",
                ],
            )
            page = await browser.new_page()
            
            await page.goto(url, wait_until="domcontentloaded")
            
            await page.wait_for_timeout(2000)
            
            title = await page.title()
            
            html_content = await page.content()
            
            await browser.close()
        
        soup = BeautifulSoup(html_content, 'html.parser')

        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
            element.decompose()

        main_content = None

        for selector in ['main', 'article', '[role="main"]', '.main-content', '#main-content', '.content', '#content']:
            main_content = soup.select_one(selector)
            if main_content:
                break

        if not main_content:
            main_content = soup.body

        if main_content:
            text_parts = []

            for element in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'td', 'th']):
                text = element.get_text(strip=True)
                if text:
                    text_parts.append(text)
            
            content = '\n\n'.join(text_parts)
        else:
            content = soup.get_text(separator='\n\n', strip=True)

        content = re.sub(r'\n{3,}', '\n\n', content)
        
        validation = self._validate_content(content, title, url)
        
        result = {
            "type": "web_page",
            "title": title,
            "content": content,
            "url": url,
            "is_valid": validation['is_valid'],
            "validation_reason": validation['reason'],
            "validation_message": validation['message']
        }
        
        if validation['warnings']:
            result['validation_warnings'] = validation['warnings']
        
        return result
    

    def _extract_pdf_text(self, path: str) -> str:
        """Extract text from a PDF using PyMuPDF"""
        full_text = ""
        with pymupdf.open(path) as pdf:
            for page in pdf:
                full_text += page.get_text() + "\n\n"
        return full_text


    def _extract_excel_text(self, path: str) -> str:
        """Extract text from an Excel file (.xlsx)"""
        text_parts = []
        
        excel_data = pd.read_excel(path, sheet_name=None, engine='openpyxl')
        
        for sheet_name, df in excel_data.items():
            text_parts.append(f"Sheet: {sheet_name}")
            text_parts.append("=" * 50)

            df_str = df.fillna('').to_string(index=False)
            text_parts.append(df_str)
            text_parts.append("")
        
        return '\n\n'.join(text_parts)
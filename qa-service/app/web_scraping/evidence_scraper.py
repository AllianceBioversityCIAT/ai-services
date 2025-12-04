"""
Evidence Scraper Module
Integra el web scraping de evidencias con el servicio de QA
"""

import os
import re
import asyncio
from typing import List, Dict, Optional
from app.utils.logger.logger_util import get_logger
from app.web_scraping.web_scraping import WebScraperService

logger = get_logger()


class EvidenceEnhancer:
    def __init__(self, download_dir: Optional[str] = None):
        self.scraper = WebScraperService(download_dir=download_dir)
        self.download_dir = self.scraper.download_dir
        logger.info(f"🔍 Evidence scraper initialized with download dir: {self.download_dir}")
    

    async def extract_evidence_content(self, evidence_urls: List[str], max_content_length: int = 40000, cleanup_files: bool = True) -> List[Dict]:
        evidence_contents = []
        
        logger.info(f"📚 Processing {len(evidence_urls)} evidence URLs")
        
        for idx, url in enumerate(evidence_urls, 1):
            try:
                logger.info(f"🔗 [{idx}/{len(evidence_urls)}] Scraping: {url}")
                
                result = await self.scraper.scrape_url(url)
                
                is_valid = result.get('is_valid', True)
                validation_reason = result.get('validation_reason', 'unknown')
                validation_message = result.get('validation_message', '')
                
                if not is_valid:
                    logger.warning(f"⚠️ Invalid content detected for {url}")
                    logger.warning(f"   Reason: {validation_reason}")
                    logger.warning(f"   Message: {validation_message}")
                    
                    if cleanup_files and 'file_path' in result:
                        self._cleanup_file(result['file_path'])
                    
                    evidence_contents.append({
                        "url": url,
                        "type": "invalid_content",
                        "title": result.get('title', 'Invalid Content'),
                        "content": "",
                        "error": validation_message,
                        "validation_reason": validation_reason,
                        "full_length": 0
                    })
                    continue
                
                content = result['content']

                content, refs_removed = self._remove_references_section(content, result['title'])

                if 'validation_warnings' in result and result['validation_warnings']:
                    logger.warning(f"⚠️ Validation warnings for {url}:")
                    for warning in result['validation_warnings']:
                        logger.warning(f"   - {warning}")
                
                if len(content) > max_content_length:
                    content = content[:max_content_length] + f"\n\n[Content truncated - original length: {len(result['content'])} chars]"
                
                evidence_data = {
                    "url": url,
                    "type": result['type'],
                    "title": result['title'],
                    "content": content,
                    "full_length": len(result['content']),
                    "is_valid": True
                }
                
                if 'file_path' in result:
                    evidence_data['file_path'] = result['file_path']
                
                if 'validation_warnings' in result:
                    evidence_data['validation_warnings'] = result['validation_warnings']
                
                evidence_contents.append(evidence_data)
                logger.info(f"✅ Successfully scraped: {result['title']} ({result['type']})")
                logger.info(f"Content preview: {content[:200]}...\n")
                
                if cleanup_files and 'file_path' in result:
                    self._cleanup_file(result['file_path'])
                
            except Exception as e:
                logger.error(f"❌ Error scraping {url}: {str(e)}")
                evidence_contents.append({
                    "url": url,
                    "type": "error",
                    "title": "Failed to scrape",
                    "content": "",
                    "error": str(e),
                    "full_length": 0,
                    "is_valid": False
                })
        
        return evidence_contents
    

    def _remove_references_section(self, content: str, title: str = "") -> tuple:
        reference_headers = [
            r'\n\s*references?\s*\n',
            r'\n\s*bibliography\s*\n',
            r'\n\s*works?\s+cited\s*\n',
            r'\n\s*literatura?\s+citada\s*\n',
            r'\n\s*bibliograf[ií]a\s*\n',
            r'\n\s*referencias?\s+bibliogr[áa]ficas?\s*\n'
        ]
        
        original_length = len(content)
        
        cutoff_point = int(len(content) * 0.6)
        search_area = content[cutoff_point:]
        
        for pattern in reference_headers:
            match = re.search(pattern, search_area, re.IGNORECASE)
            if match:
                match_pos = cutoff_point + match.start()
                
                sample_after = content[match_pos:match_pos + 1000]
                
                year_indicators = len(re.findall(r'\b\d{4}\b', sample_after))
                doi_indicators = len(re.findall(r'doi:', sample_after, re.IGNORECASE))
                url_indicators = len(re.findall(r'https?://', sample_after))
                et_al_indicators = len(re.findall(r'\bet al\.', sample_after, re.IGNORECASE))
                
                author_year_pattern = len(re.findall(r'[A-Z][a-z]+\s+[A-Z]{1,3}[,\.].*?\d{4}', sample_after))
                journal_pattern = len(re.findall(r'\.\s+[A-Z][a-zA-Z\s]+\.\s+\d{4}', sample_after))
                
                lines_after = sample_after.split('\n')[:10]
                reference_like_lines = sum(1 for line in lines_after 
                                          if line.strip() and 
                                          re.search(r'^[A-Z].*\d{4}', line.strip()))
                
                total_indicators = (
                    year_indicators + 
                    doi_indicators * 2 +
                    url_indicators + 
                    et_al_indicators * 2 +
                    author_year_pattern * 2 +
                    journal_pattern * 2 +
                    reference_like_lines * 3
                )
                
                if total_indicators >= 5:
                    content = content[:match_pos].strip()
                    removed_chars = original_length - len(content)
                    logger.info(f"📚 Removed references section from '{title}' ({removed_chars} chars, {total_indicators} indicators)")
                    return content, True
        
        return content, False
    

    def _cleanup_file(self, file_path: str):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"🗑️ Cleaned up file: {file_path}")
        except Exception as e:
            logger.warning(f"⚠️ Could not delete file {file_path}: {str(e)}")
    

    def format_evidence_for_prompt(self, evidence_contents: List[Dict]) -> str:
        if not evidence_contents:
            return ""
        
        valid_evidences = [
            e for e in evidence_contents 
            if e['type'] not in ['error', 'invalid_content'] and e.get('is_valid', True)
        ]
        
        if not valid_evidences:
            return ""
        
        formatted_parts = []
        formatted_parts.append("=== ADDITIONAL CONTEXT FROM EVIDENCE SOURCES ===\n")
        
        for idx, evidence in enumerate(valid_evidences, 1):
            formatted_parts.append(f"\nEvidence {idx}: {evidence['title']}")
            formatted_parts.append(f"Source: {evidence['url']}")
            formatted_parts.append(f"Type: {evidence['type']}")
            
            if 'validation_warnings' in evidence and evidence['validation_warnings']:
                formatted_parts.append("\nWarnings:")
                for warning in evidence['validation_warnings']:
                    formatted_parts.append(f"  - {warning}")
            
            formatted_parts.append(f"\nContent:\n{evidence['content']}")
            formatted_parts.append("\n" + "-" * 80 + "\n")
        
        return "\n".join(formatted_parts)
    

    async def enhance_prms_context(
        self, 
        result_metadata: dict, 
        evidence_urls: Optional[List[str]] = None,
        max_evidences: int = 5
    ) -> Dict:
        
        if not evidence_urls:
            logger.warning("⚠️ No evidence URLs provided")
            return {
                "evidence_contents": [],
                "formatted_context": "",
                "evidence_count": 0
            }
        
        if len(evidence_urls) > max_evidences:
            logger.info(f"⚠️ Limiting evidence processing to {max_evidences} URLs")
            evidence_urls = evidence_urls[:max_evidences]
        
        evidence_contents = await self.extract_evidence_content(evidence_urls)
        
        formatted_context = self.format_evidence_for_prompt(evidence_contents)
        
        successful_count = sum(
            1 for e in evidence_contents 
            if e['type'] not in ['error', 'invalid_content'] and e.get('is_valid', True)
        )
        invalid_count = sum(
            1 for e in evidence_contents 
            if e['type'] == 'invalid_content'
        )
        error_count = sum(
            1 for e in evidence_contents 
            if e['type'] == 'error'
        )
        
        logger.info(f"📊 Evidence processing complete:")
        logger.info(f"   Valid: {successful_count}/{len(evidence_urls)}")
        if invalid_count > 0:
            logger.warning(f"   Invalid content: {invalid_count}")
        if error_count > 0:
            logger.error(f"   Errors: {error_count}")
        
        return {
            "evidence_contents": evidence_contents,
            "formatted_context": formatted_context,
            "evidence_count": successful_count,
            "invalid_count": invalid_count,
            "error_count": error_count,
            "total_attempted": len(evidence_urls)
        }
    

async def get_evidence_context(evidence_urls: List[str]) -> str:
    enhancer = EvidenceEnhancer()
    evidence_contents = await enhancer.extract_evidence_content(evidence_urls)
    return enhancer.format_evidence_for_prompt(evidence_contents)

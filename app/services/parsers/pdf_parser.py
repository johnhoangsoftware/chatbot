"""
PDF parser - wraps existing TechnicalDocumentParser for PDF files.
"""

import fitz  # PyMuPDF
import os
import re
from typing import List, Dict, Any, Optional
from .base import BaseParser, ParsedDocument, Section, TableData

# Import the existing TechnicalDocumentParser
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

class PDFParser(BaseParser):
    """Parser for PDF files using the existing TechnicalDocumentParser."""

    # Patterns for technical document parsing
    HEADING_PATTERNS = [
        r'^(\d+\.)+\s+',  # 1.2.3 Style numbering
        r'^[A-Z][A-Z\s]{2,}$',  # ALL CAPS headers
        r'^(?:Chapter|Section|Part|Appendix)\s+\d+',  # Chapter/Section markers
        r'^(?:SWE|SYS|MAN|SUP|ACQ)\.\d+',  # ASPICE process IDs
        r'^(?:ASIL|QM)\s*[A-D]?',  # ISO 26262 ASIL levels
    ]
    
    CODE_INDICATORS = [
        'void ', 'int ', 'char ', 'float ', 'double ',
        'class ', 'struct ', 'enum ', 'typedef ',
        '#include', '#define', '#ifdef',
        'function()', '{}', ';',
    ]
    
    def __init__(self):
        self.heading_regex = [re.compile(p, re.IGNORECASE) for p in self.HEADING_PATTERNS]
    
    @property
    def supported_extensions(self) -> List[str]:
        return ['.pdf']
    
    def parse(self, file_path: str) -> ParsedDocument:
        """Parse a PDF file."""
        if not self.validate(file_path):
            raise ValueError(f"Invalid or unsupported file: {file_path}")
        
        return self._parse_technical_pdf(file_path)
    
    def _parse_technical_pdf(self, file_path: str) -> ParsedDocument:
        """Parse PDF with technical document optimizations."""
        doc = fitz.open(file_path)
        
        pages = []
        all_sections = []
        all_tables = []
        full_content = []
        toc = []
        
        # Extract TOC if available
        try:
            pdf_toc = doc.get_toc()
            for item in pdf_toc:
                level, title, page = item
                toc.append({
                    "level": level,
                    "title": title,
                    "page": page
                })
        except:
            pass
        
        for page_num, page in enumerate(doc, start=1):
            # Extract text with layout preservation
            text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            
            # Process blocks
            page_text = []
            page_sections = []
            page_tables = []
            
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:  # Text block
                    block_text = self._extract_block_text(block)
                    
                    # Detect if this is a heading
                    section = self._detect_section(block_text, page_num, block)
                    if section:
                        page_sections.append(section)
                    
                    page_text.append(block_text)
                    
                elif block.get("type") == 1:  # Image block
                    # Note image presence for context
                    page_text.append(f"[Figure on page {page_num}]")
            
            # Try to extract tables
            try:
                tables = page.find_tables()
                for table in tables:
                    table_data = self._extract_table(table, page_num)
                    if table_data:
                        page_tables.append(table_data)
                        page_text.append(f"\n[Table]\n{table_data.content}\n[/Table]\n")
            except:
                pass
            
            # Combine page content
            page_content = "\n".join(page_text)
            page_content = self._clean_technical_text(page_content)
            
            # Detect code blocks
            page_content = self._mark_code_blocks(page_content)
            
            pages.append({
                "page_number": page_num,
                "content": page_content,
                "word_count": len(page_content.split()),
                "char_count": len(page_content),
                "has_tables": len(page_tables) > 0,
                "has_figures": "[Figure" in page_content,
                "sections": [s.title for s in page_sections]
            })
            
            all_sections.extend(page_sections)
            all_tables.extend(page_tables)
            full_content.append(f"[Page {page_num}]\n{page_content}")
        
        # Build metadata
        metadata = {
            "filename": os.path.basename(file_path),
            "file_path": file_path,
            "page_count": len(doc),
            "total_words": sum(p["word_count"] for p in pages),
            "total_chars": sum(p["char_count"] for p in pages),
            "table_count": len(all_tables),
            "section_count": len(all_sections),
            "has_toc": len(toc) > 0,
            "pdf_metadata": dict(doc.metadata) if doc.metadata else {},
            "document_type": self._detect_document_type(full_content, toc)
        }
        
        doc.close()
        
        return ParsedDocument(
            filename=os.path.basename(file_path),
            content="\n\n".join(full_content),
            pages=pages,
            metadata=metadata,
            sections=all_sections,
            tables=all_tables,
            toc=toc
        )
    
    def _extract_block_text(self, block: Dict) -> str:
        """Extract text from a block with line handling."""
        lines = []
        for line in block.get("lines", []):
            line_text = ""
            for span in line.get("spans", []):
                text = span.get("text", "")
                line_text += text
            if line_text.strip():
                lines.append(line_text)
        
        return "\n".join(lines)
    
    def _detect_section(self, text: str, page_num: int, block: Dict) -> Optional[Section]:
        """Detect if text is a section heading."""
        text = text.strip()
        if not text or len(text) > 200:
            return None
        
        # Check against heading patterns
        for regex in self.heading_regex:
            if regex.match(text):
                # Determine level based on pattern and font size
                level = self._determine_heading_level(text, block)
                return Section(
                    title=text,
                    level=level,
                    content="",
                    page_number=page_num
                )
        
        # Check for large/bold font (typical heading)
        if block.get("lines"):
            first_line = block["lines"][0]
            if first_line.get("spans"):
                span = first_line["spans"][0]
                font_size = span.get("size", 12)
                flags = span.get("flags", 0)
                is_bold = flags & 2 ** 4  # Bold flag
                
                if font_size > 14 or (font_size > 12 and is_bold):
                    if len(text) < 100:  # Headings are usually short
                        level = 1 if font_size > 16 else 2 if font_size > 14 else 3
                        return Section(
                            title=text,
                            level=level,
                            content="",
                            page_number=page_num
                        )
        
        return None
    
    def _determine_heading_level(self, text: str, block: Dict) -> int:
        """Determine heading level based on numbering pattern."""
        # Count dots in numbering
        match = re.match(r'^([\d\.]+)', text)
        if match:
            dots = match.group(1).count('.')
            return min(dots + 1, 6)
        
        return 2  # Default level
    
    def _extract_table(self, table, page_num: int) -> Optional[TableData]:
        """Extract table content."""
        try:
            # Get table data
            data = table.extract()
            if not data:
                return None
            
            rows = len(data)
            cols = max(len(row) for row in data) if data else 0
            
            # Format as text
            content_lines = []
            for row in data:
                row_text = " | ".join(str(cell) if cell else "" for cell in row)
                content_lines.append(row_text)
            
            content = "\n".join(content_lines)
            
            return TableData(
                page_number=page_num,
                content=content,
                rows=rows,
                columns=cols
            )
        except:
            return None
    
    def _clean_technical_text(self, text: str) -> str:
        """Clean and normalize technical text."""
        # Fix common OCR issues in technical docs
        text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)  # CamelCase spacing
        
        # Normalize whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        # Fix common technical abbreviations
        text = re.sub(r'\bAPSICE\b', 'ASPICE', text, flags=re.IGNORECASE)
        text = re.sub(r'\bAUTOSAR\b', 'AUTOSAR', text)
        
        # Preserve bullet points and numbered lists
        text = re.sub(r'^[-•]\s*', '• ', text, flags=re.MULTILINE)
        
        return text.strip()
    
    def _mark_code_blocks(self, text: str) -> str:
        """Detect and mark code blocks in text."""
        lines = text.split('\n')
        result = []
        in_code_block = False
        code_block = []
        
        for line in lines:
            is_code_line = any(indicator in line for indicator in self.CODE_INDICATORS)
            
            if is_code_line and not in_code_block:
                in_code_block = True
                code_block = [line]
            elif is_code_line and in_code_block:
                code_block.append(line)
            elif in_code_block and not is_code_line:
                # End code block
                if len(code_block) >= 2:
                    result.append("[CODE]")
                    result.extend(code_block)
                    result.append("[/CODE]")
                else:
                    result.extend(code_block)
                in_code_block = False
                code_block = []
                result.append(line)
            else:
                result.append(line)
        
        # Handle remaining code block
        if code_block:
            if len(code_block) >= 2:
                result.append("[CODE]")
                result.extend(code_block)
                result.append("[/CODE]")
            else:
                result.extend(code_block)
        
        return '\n'.join(result)
    
    def _detect_document_type(self, content: List[str], toc: List[Dict]) -> str:
        """Detect the type of technical document."""
        full_text = " ".join(content).lower()
        
        # Check for ASPICE
        if 'aspice' in full_text or 'automotive spice' in full_text:
            if 'assessment' in full_text:
                return "ASPICE Assessment Report"
            return "ASPICE Document"
        
        # Check for ISO 26262
        if 'iso 26262' in full_text or 'functional safety' in full_text:
            if 'hazard' in full_text and 'risk' in full_text:
                return "HARA Document"
            if 'safety case' in full_text:
                return "Safety Case"
            return "Functional Safety Document"
        
        # Check for AUTOSAR
        if 'autosar' in full_text:
            if 'sws' in full_text or 'software specification' in full_text:
                return "AUTOSAR SWS"
            if 'arxml' in full_text:
                return "AUTOSAR Configuration"
            return "AUTOSAR Document"
        
        # Check for requirements
        if 'requirement' in full_text and ('shall' in full_text or 'must' in full_text):
            return "Requirements Specification"
        
        # Check for design docs
        if 'architecture' in full_text or 'design' in full_text:
            return "Design Document"
        
        # Check for test docs
        if 'test case' in full_text or 'test specification' in full_text:
            return "Test Specification"
        
        return "Technical Document"
    
    def extract_requirements(self, parsed_doc: ParsedDocument) -> List[Dict[str, Any]]:
        """Extract requirements from a parsed document."""
        requirements = []
        
        # Patterns for requirement IDs
        req_patterns = [
            r'(REQ[-_]?\d+[-_]?\d*)',
            r'(SWE[-_]?\d+[-_]?\d*)',
            r'(SYS[-_]?\d+[-_]?\d*)',
            r'(\[R\d+\])',
        ]
        
        # Pattern for requirement text (shall/must statements)
        shall_pattern = re.compile(
            r'([^.]*(?:shall|must|should|may)[^.]*\.)',
            re.IGNORECASE
        )
        
        for page in parsed_doc.pages:
            content = page["content"]
            
            # Find requirement IDs
            for pattern in req_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    req_id = match.group(1)
                    # Find the associated text
                    start = match.end()
                    end = min(start + 500, len(content))
                    context = content[start:end]
                    
                    # Extract the requirement statement
                    shall_match = shall_pattern.search(context)
                    if shall_match:
                        requirements.append({
                            "id": req_id,
                            "text": shall_match.group(1).strip(),
                            "page": page["page_number"]
                        })
        
        return requirements

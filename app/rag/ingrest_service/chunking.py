# ingest_service/chunking.py
# fast chunking of documents
from langchain_text_splitters import RecursiveCharacterTextSplitter
import re

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)

def chunk(raw_doc):
    chunks = splitter.split_text(raw_doc["content"])
    output = []

    for idx, text in enumerate(chunks):
        output.append({
            "chunk_id": raw_doc["raw_id"] + f"_c{idx}",
            "raw_id": raw_doc["raw_id"],
            "text": text,
            "metadata": raw_doc["metadata"] | {
                "chunk_index": idx,
                "source_type": raw_doc["source_type"],
                "path": raw_doc["path"]
            }
        })
    return output


HEADING_PATTERNS = [
    r"^\d+\.\s+[^\n]{1,200}$",                 # 1. Title
    r"^\d+(?:\.\d+){1,4}\s+[^\n]{1,200}$",     # 1.1 Title, 2.3.4 Title
    r"^\d+\)\s+[^\n]{1,200}$",                 # 1) Title
    r"^(?:[IVXLCDM]+\.?)\s+[^\n]{1,200}$",     # I. Title / II Title
    r"^[A-Z]\.\s+[^\n]{1,200}$",               # A. Title
    r"^#{1,6}\s+[^\n]{1,200}$",                # # Markdown headers
]


SENTENCE_OR_LIST_END = re.compile(r'[.!?…][)\]}"\'»”’»\]]*\s*$', re.UNICODE) # Check if that is a list or sentence when it format similar to a heading

def _compile_patterns():
    return [re.compile(pattern, flags=re.MULTILINE) for pattern in HEADING_PATTERNS]

def _find_first_heading_and_pattern(text, compiled_patterns):
    """
    Find the earliest match across all patterns. Only take first heading, the rest treated as paragraph
    Return (pattern_index, first_match_obj) or (None, None).
    """
    earliest = None  # (start_position, pattern_idx, first_match_obj)
    for idx, compiled_pattern in enumerate(compiled_patterns):
        for matched in compiled_pattern.finditer(text):
            start = matched.start()
            if earliest is None or start < earliest[0]:
                earliest = (start, idx, matched)
            if earliest and earliest[0] == 0:
                break
        if earliest and earliest[0] == 0:
            break
    if earliest is None:
        return None, None
    return earliest[1], earliest[2]

def _collect_matches_for_pattern(text, compiled_pattern):
    """Collect all matches for the chosen pattern in document order."""
    return list(compiled_pattern.finditer(text))

def _looks_like_list_or_sentence(line: str) -> bool:
    """
    Heuristic: a numbered line that ends with sentence punctuation is
    likely a list item or a paragraph, not a section title.
    """
    if SENTENCE_OR_LIST_END.search(line.strip()):
        return True
    
    return False

def chunk_by_structure(raw_doc):
    """
    Chunk by the first heading *pattern* encountered.
    - Only split on headings of that same pattern.
    - If subsequent lines that match the pattern look like list items(end with a period), 
    treat them as content, NOT boundaries.
    - Preamble (before the first chosen-pattern heading) is prepended to the first chunk.
    - If no headings, return the whole content as one chunk.
    """
    text = raw_doc["content"]
    compiled = _compile_patterns()

    # 1) Identify the first heading and its pattern
    chosen_idx, first_match = _find_first_heading_and_pattern(text, compiled)

    if chosen_idx is None:
        # No headings -> single chunk
        return [{
            "chunk_id": f'{raw_doc["raw_id"]}_c0',
            "raw_id": raw_doc["raw_id"],
            "text": text,
            "metadata": raw_doc["metadata"] | {
                "chunk_index": 0,
                "source_type": raw_doc["source_type"],
                "path": raw_doc["path"],
            }
        }]

    chosen_pattern = compiled[chosen_idx]

    # 2) Gather all matches of the chosen pattern (from entire text), but we will
    # treat only some as *boundaries* based on heuristics.
    all_matches = _collect_matches_for_pattern(text, chosen_pattern)
    # Keep only matches at/after the first chosen heading
    all_matches = [matched for matched in all_matches if matched.start() >= first_match.start()]

    # 3) Decide which matches are actual section boundaries.
    boundaries = []
    for idx, matched in enumerate(all_matches):
        line = matched.group(0).strip()  # full matched heading line
        if idx == 0:
            # Always treat the very first encountered heading as a boundary
            boundaries.append(matched)
        else:
            # If it looks like a list/sentence (start with heading 1., 2., ... but ends with '.'), do NOT split here
            if not _looks_like_list_or_sentence(line):
                boundaries.append(matched)

    output = []

    # 4) Preamble (before first boundary)
    preamble = text[:boundaries[0].start()] if boundaries else text[:first_match.start()]

    # 5) Build chunks using boundaries
    for idx, matched in enumerate(boundaries):
        start = matched.start()
        end = boundaries[idx + 1].start() if (idx + 1) < len(boundaries) else len(text)

        section_text = text[start:end]

        # Attach preamble to the first section
        if idx == 0 and preamble.strip():
            section_text = preamble.rstrip() + "\n\n" + section_text.lstrip()

        output.append({
            "chunk_id": f'{raw_doc["raw_id"]}_c{idx}',
            "raw_id": raw_doc["raw_id"],
            "text": section_text,
            "metadata": raw_doc["metadata"] | {
                "chunk_index": idx,
                "source_type": raw_doc["source_type"],
                "path": raw_doc["path"],

            }
        })

    return output

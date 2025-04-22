# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import logging
from typing import Dict, Any, List, Optional, Tuple, Union
import os

# Try to import document analysis dependencies
try:
    from langchain.document_loaders import TextLoader, PyPDFLoader, CSVLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False
    logging.warning("langchain is not installed. Document analysis will be limited.")

# Check for NLP libraries
try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize, sent_tokenize
    HAS_NLTK = True
    # Download required NLTK data
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
except ImportError:
    HAS_NLTK = False
    logging.warning("nltk is not installed. Document analysis capabilities will be limited.")

class AnalysisResult(Dict[str, Any]):
    """Document analysis result dictionary"""
    pass

async def analyze_document(file_path: str, 
                        analysis_type: str = "basic",
                        options: Optional[Dict[str, Any]] = None) -> AnalysisResult:
    """Analyze a document file
    
    Args:
        file_path: Path to the document file
        analysis_type: Type of analysis to perform (basic, structure, content, code)
        options: Additional options for the analysis
        
    Returns:
        Document analysis results
    """
    if not os.path.exists(file_path):
        return AnalysisResult({
            "success": False,
            "error": f"File not found: {file_path}"
        })
        
    options = options or {}
    
    try:
        # Basic file information analysis
        file_info = _analyze_file_info(file_path)
        
        if analysis_type == "basic":
            return AnalysisResult({
                "success": True,
                "file_info": file_info,
                "analysis_type": "basic"
            })
            
        # Load document content based on file type
        content = _load_document(file_path)
        
        # Perform the requested analysis
        if analysis_type == "structure":
            structure = _analyze_structure(content, options)
            return AnalysisResult({
                "success": True,
                "file_info": file_info,
                "structure": structure,
                "analysis_type": "structure"
            })
            
        elif analysis_type == "content":
            content_analysis = _analyze_content(content, options)
            return AnalysisResult({
                "success": True,
                "file_info": file_info,
                "content_analysis": content_analysis,
                "analysis_type": "content"
            })
            
        elif analysis_type == "code":
            code_analysis = _analyze_code(content, options)
            return AnalysisResult({
                "success": True,
                "file_info": file_info,
                "code_analysis": code_analysis,
                "analysis_type": "code"
            })
            
        else:
            return AnalysisResult({
                "success": False,
                "error": f"Unknown analysis type: {analysis_type}"
            })
            
    except Exception as e:
        logging.error(f"Error analyzing document: {str(e)}")
        return AnalysisResult({
            "success": False,
            "error": str(e)
        })

def _analyze_file_info(file_path: str) -> Dict[str, Any]:
    """Extract basic file information
    
    Args:
        file_path: Path to the file
        
    Returns:
        File information dictionary
    """
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1].lower()
    file_size = os.path.getsize(file_path)
    file_type = _get_file_type(file_ext)
    
    return {
        "name": file_name,
        "extension": file_ext,
        "size_bytes": file_size,
        "size_readable": _format_size(file_size),
        "type": file_type,
        "path": file_path
    }

def _get_file_type(extension: str) -> str:
    """Determine file type from extension
    
    Args:
        extension: File extension
        
    Returns:
        File type description
    """
    extension = extension.lower()
    
    if extension in ['.txt', '.md', '.rst']:
        return "text"
    elif extension in ['.pdf']:
        return "pdf"
    elif extension in ['.csv', '.tsv']:
        return "tabular"
    elif extension in ['.py', '.js', '.ts', '.java', '.c', '.cpp', '.go', '.rs']:
        return "code"
    elif extension in ['.json', '.yaml', '.yml', '.toml']:
        return "config"
    elif extension in ['.html', '.htm', '.xml']:
        return "markup"
    elif extension in ['.docx', '.doc', '.odt']:
        return "document"
    else:
        return "unknown"

def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def _load_document(file_path: str) -> str:
    """Load document content based on file type
    
    Args:
        file_path: Path to the document
        
    Returns:
        Document content as string
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # If langchain is available, use its loaders
    if HAS_LANGCHAIN:
        try:
            if file_ext == '.pdf':
                loader = PyPDFLoader(file_path)
                docs = loader.load()
                return "\n".join([doc.page_content for doc in docs])
            elif file_ext == '.csv':
                loader = CSVLoader(file_path)
                docs = loader.load()
                return "\n".join([doc.page_content for doc in docs])
            # For other file types, fall back to text loader
        except Exception as e:
            logging.warning(f"Error using LangChain loader: {str(e)}")
    
    # Basic text loading for all other cases
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()

def _analyze_structure(content: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze document structure
    
    Args:
        content: Document content
        options: Analysis options
        
    Returns:
        Structure analysis results
    """
    # Split content into sections and paragraphs
    lines = content.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    
    # Identify headers and sections
    headers = []
    for i, line in enumerate(non_empty_lines):
        line = line.strip()
        # Simple heuristic for headers: short lines with special formatting
        if len(line) < 100 and (line.startswith('#') or line.isupper() or 
                              line.endswith(':') or line.startswith('=====')):
            headers.append({
                "text": line,
                "line_number": i
            })
    
    # Count paragraphs (heuristic: groups of non-empty lines)
    paragraph_count = 0
    in_paragraph = False
    
    for line in lines:
        if line.strip():
            if not in_paragraph:
                paragraph_count += 1
                in_paragraph = True
        else:
            in_paragraph = False
    
    # Parse sentences if NLTK is available
    sentences = []
    if HAS_NLTK:
        sentences = sent_tokenize(content)
    
    return {
        "line_count": len(lines),
        "non_empty_line_count": len(non_empty_lines),
        "character_count": len(content),
        "word_count": len(content.split()),
        "paragraph_count": paragraph_count,
        "sentence_count": len(sentences),
        "headers": headers[:10],  # Limit to first 10 headers
        "has_tabular_content": '\t' in content or '|' in content,
        "has_code_blocks": '```' in content or '    ' in content
    }

def _analyze_content(content: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze document content
    
    Args:
        content: Document content
        options: Analysis options
        
    Returns:
        Content analysis results
    """
    # Basic statistics
    word_count = len(content.split())
    char_count = len(content)
    
    # Advanced NLP analysis if NLTK is available
    if HAS_NLTK:
        words = word_tokenize(content.lower())
        stop_words = set(stopwords.words('english'))
        words_no_stop = [word for word in words if word.isalnum() and word not in stop_words]
        
        # Get most common words
        word_freq = {}
        for word in words_no_stop:
            if word in word_freq:
                word_freq[word] += 1
            else:
                word_freq[word] = 1
                
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        top_words = sorted_words[:20]  # Top 20 words
        
        # Calculate readability (simple metric)
        sentences = sent_tokenize(content)
        avg_sentence_length = word_count / len(sentences) if sentences else 0
        
        return {
            "word_count": word_count,
            "character_count": char_count,
            "unique_words": len(word_freq),
            "top_words": dict(top_words),
            "avg_sentence_length": avg_sentence_length,
            "readability_score": _calculate_readability(content) if sentences else 0
        }
    else:
        # Basic analysis without NLTK
        return {
            "word_count": word_count,
            "character_count": char_count
        }

def _calculate_readability(text: str) -> float:
    """Calculate simple readability score (0-100)
    
    Args:
        text: Text content
        
    Returns:
        Readability score
    """
    if not HAS_NLTK:
        return 0
        
    sentences = sent_tokenize(text)
    words = word_tokenize(text)
    
    if not sentences or not words:
        return 0
        
    # Average words per sentence
    avg_words = len(words) / len(sentences)
    
    # Count complex words (more than 3 syllables, simple approximation)
    complex_word_count = 0
    for word in words:
        syllables = _count_syllables(word)
        if syllables > 3:
            complex_word_count += 1
            
    # Percentage of complex words
    complex_ratio = complex_word_count / len(words) if words else 0
    
    # Simplified Flesch Reading Ease formula
    score = 206.835 - (1.015 * avg_words) - (84.6 * complex_ratio)
    
    # Ensure score is between 0-100
    return max(0, min(100, score))

def _count_syllables(word: str) -> int:
    """Count syllables in a word (approximate)
    
    Args:
        word: Input word
        
    Returns:
        Estimated syllable count
    """
    word = word.lower()
    
    # Special cases
    if len(word) <= 3:
        return 1
        
    # Remove punctuation
    word = ''.join(c for c in word if c.isalnum())
    
    # Count vowel sequences
    vowels = "aeiouy"
    count = 0
    prev_is_vowel = False
    
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_is_vowel:
            count += 1
        prev_is_vowel = is_vowel
    
    # Handle special cases
    if word.endswith('e'):
        count -= 1
    if word.endswith('le') and len(word) > 2 and word[-3] not in vowels:
        count += 1
    if count == 0:
        count = 1
        
    return count

def _analyze_code(content: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze code content
    
    Args:
        content: Code content
        options: Analysis options
        
    Returns:
        Code analysis results
    """
    lines = content.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    
    # Count comment lines (simplified heuristic)
    comment_lines = 0
    for line in lines:
        line = line.strip()
        if line.startswith('#') or line.startswith('//') or line.startswith('/*') or line.startswith('*'):
            comment_lines += 1
    
    # Detect programming language
    language = options.get('language', _detect_language(content))
    
    # Identify imports/includes
    imports = []
    for line in lines:
        line = line.strip()
        if any(line.startswith(s) for s in ['import ', 'from ', '#include', 'using ']):
            imports.append(line)
    
    # Count functions/methods (simplified heuristic)
    function_count = 0
    for i, line in enumerate(lines):
        if re.search(r'def\s+\w+\s*\(', line) or re.search(r'function\s+\w+\s*\(', line) or re.search(r'\w+\s*\([^)]*\)\s*{', line):
            function_count += 1
    
    # Count classes (simplified heuristic)
    class_count = 0
    for line in lines:
        if re.search(r'class\s+\w+', line):
            class_count += 1
    
    return {
        "language": language,
        "line_count": len(lines),
        "non_empty_line_count": len(non_empty_lines),
        "comment_line_count": comment_lines,
        "comment_ratio": comment_lines / len(non_empty_lines) if non_empty_lines else 0,
        "function_count": function_count,
        "class_count": class_count,
        "imports": imports[:10]  # Limit to first 10 imports
    }

def _detect_language(content: str) -> str:
    """Detect programming language from content
    
    Args:
        content: Code content
        
    Returns:
        Detected programming language
    """
    # Simple heuristics for language detection
    if re.search(r'import\s+[a-zA-Z0-9_.]+|from\s+[a-zA-Z0-9_.]+\s+import', content):
        return "python"
    elif re.search(r'#include\s+[<"][a-zA-Z0-9_.]+[>"]', content):
        if '{' in content and '}' in content:
            return "c" if 'malloc(' in content or 'printf(' in content else "cpp"
        return "c/cpp"
    elif re.search(r'package\s+[a-zA-Z0-9_.]+;|import\s+java\.[a-zA-Z0-9_.]+;', content):
        return "java"
    elif re.search(r'func\s+\w+\s*\(', content) and 'package' in content:
        return "go"
    elif 'function' in content and 'var ' in content or 'let ' in content or 'const ' in content:
        if 'import React' in content or 'export default' in content:
            return "jsx"
        return "javascript"
    elif '{' in content and '}' in content and ';' in content:
        return "c-family"
    else:
        return "unknown"

# Import needed for some functions
import re
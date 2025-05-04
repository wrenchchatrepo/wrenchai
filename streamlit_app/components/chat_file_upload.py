"""Chat File Upload Component.

This component enables file uploads within a chat interface.
"""

import streamlit as st
from typing import List, Dict, Any, Optional
import os
import uuid
import base64

def chat_file_uploader(allowed_types: Optional[List[str]] = None, 
                     max_size_mb: int = 10,
                     key: str = "chat_files"):
    """File upload component for chat interfaces.
    
    Args:
        allowed_types: List of allowed file extensions (None for all types)
        max_size_mb: Maximum file size in MB
        key: Session state key for this component
    
    Returns:
        List of uploaded file info dictionaries
    """
    # Initialize session state for this component
    if f"{key}_uploads" not in st.session_state:
        st.session_state[f"{key}_uploads"] = []
    
    # Show previously uploaded files
    if st.session_state[f"{key}_uploads"]:
        st.markdown("### Attached Files")
        for i, file_info in enumerate(st.session_state[f"{key}_uploads"]):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{file_info['name']}** ({file_info['size_formatted']})")  
            with col2:
                if st.button("Remove", key=f"remove_{key}_{i}"):
                    st.session_state[f"{key}_uploads"].pop(i)
                    st.rerun()
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Upload Files", 
        type=allowed_types,
        accept_multiple_files=True,
        key=key
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            # Check file size
            if uploaded_file.size > max_size_mb * 1024 * 1024:
                st.error(f"File {uploaded_file.name} exceeds the {max_size_mb}MB size limit")
                continue
                
            # Check if file already exists in uploads
            if any(f['name'] == uploaded_file.name for f in st.session_state[f"{key}_uploads"]):
                continue  # Skip duplicate files
                
            # Format file size
            size_bytes = uploaded_file.size
            if size_bytes < 1024:
                size_formatted = f"{size_bytes} bytes"
            elif size_bytes < 1024 * 1024:
                size_formatted = f"{size_bytes / 1024:.1f} KB"
            else:
                size_formatted = f"{size_bytes / (1024 * 1024):.1f} MB"
                
            # Create file info
            file_info = {
                'id': str(uuid.uuid4()),
                'name': uploaded_file.name,
                'type': uploaded_file.type,
                'size': size_bytes,
                'size_formatted': size_formatted,
                'content': uploaded_file.read()  # Store file content in memory
            }
            
            # Reset file pointer
            uploaded_file.seek(0)
            
            # Add to session state
            st.session_state[f"{key}_uploads"].append(file_info)
        
        # Clear the uploader
        st.rerun()
    
    return st.session_state[f"{key}_uploads"]


def get_file_extension(filename: str) -> str:
    """Get the file extension from a filename.
    
    Args:
        filename: Name of the file
        
    Returns:
        File extension (lowercase) without the dot
    """
    return os.path.splitext(filename)[1].lower().lstrip('.')


def get_file_icon(file_type: str) -> str:
    """Get an appropriate icon for the file type.
    
    Args:
        file_type: File type or extension
        
    Returns:
        Unicode icon character
    """
    file_type = file_type.lower()
    
    # Document icons
    if any(ext in file_type for ext in ['pdf', 'doc', 'docx', 'txt', 'rtf']):
        return "📄"
    # Image icons
    elif any(ext in file_type for ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg']):
        return "🖼️"
    # Archive icons
    elif any(ext in file_type for ext in ['zip', 'tar', 'gz', 'rar', '7z']):
        return "🗜️"
    # Code icons
    elif any(ext in file_type for ext in ['py', 'js', 'html', 'css', 'json', 'xml', 'java', 'c', 'cpp']):
        return "📝"
    # Spreadsheet icons
    elif any(ext in file_type for ext in ['xls', 'xlsx', 'csv']):
        return "📊"
    # Presentation icons
    elif any(ext in file_type for ext in ['ppt', 'pptx']):
        return "🎞️"
    # Audio icons
    elif any(ext in file_type for ext in ['mp3', 'wav', 'ogg', 'flac']):
        return "🎵"
    # Video icons
    elif any(ext in file_type for ext in ['mp4', 'avi', 'mov', 'mkv']):
        return "🎬"
    # Default
    else:
        return "📎"


def display_file_message(file_info: Dict[str, Any]):
    """Display a file as a chat message.
    
    Args:
        file_info: Dictionary containing file information
    """
    file_ext = get_file_extension(file_info['name'])
    icon = get_file_icon(file_ext)
    
    st.markdown(f"""
    <div style="
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 10px;
        margin: 5px 0;
    ">
        <div style="display: flex; align-items: center;">
            <div style="font-size: 24px; margin-right: 10px;">{icon}</div>
            <div>
                <div style="font-weight: bold;">{file_info['name']}</div>
                <div style="color: #BBBBBB; font-size: 0.8em;">{file_info['size_formatted']}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Preview for certain file types
    if file_ext in ['jpg', 'jpeg', 'png', 'gif']:
        try:
            # Convert bytes to base64 for embedding in HTML
            encoded = base64.b64encode(file_info['content']).decode()
            st.markdown(f"""
            <div style="max-width: 300px; margin-top: 10px;">
                <img src="data:image/{file_ext};base64,{encoded}" style="width: 100%; border-radius: 5px;">
            </div>
            """, unsafe_allow_html=True)
        except Exception:
            pass
    elif file_ext in ['txt', 'md', 'py', 'js', 'html', 'css', 'json', 'xml']:
        try:
            # Display text content for text files
            content = file_info['content'].decode('utf-8')
            with st.expander("Preview"):
                st.code(content, language=file_ext)
        except Exception:
            pass
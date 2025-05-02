# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import base64
import logging
from typing import Dict, List, Any, Optional, Union, BinaryIO
from pydantic import BaseModel, Field, HttpUrl
import mimetypes

# Try to import the Pydantic AI input types
try:
    # Import Pydantic AI's multimodal input types for rich agent interactions
    # Reference: https://ai.pydantic.dev/types/
    from pydantic_ai.types import (
        ImageUrl, BinaryContent, VideoUrl, DocumentUrl,
        AudioUrl
    )
    PYDANTIC_INPUTS_AVAILABLE = True
except ImportError:
    PYDANTIC_INPUTS_AVAILABLE = False
    logging.warning("Pydantic AI input types not available. Install with 'pip install pydantic-ai'")
    
    # Create stub classes for type checking
    class ImageUrl(BaseModel): url: HttpUrl
    class BinaryContent(BaseModel): content: bytes
    class VideoUrl(BaseModel): url: HttpUrl
    class DocumentUrl(BaseModel): url: HttpUrl
    class AudioUrl(BaseModel): url: HttpUrl

class InputProcessor:
    """Processor for handling various input types for LLM models"""
    
    def __init__(self):
        """Initialize the input processor"""
        self.supported_image_formats = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        self.supported_audio_formats = ['.mp3', '.wav', '.ogg', '.m4a']
        self.supported_document_formats = ['.pdf', '.docx', '.txt', '.md']
        self.supported_video_formats = ['.mp4', '.avi', '.mov', '.webm']
        
    def process_file_input(self, file_path: str) -> Union[ImageUrl, BinaryContent, 
                                                      VideoUrl, DocumentUrl, 
                                                      AudioUrl, None]:
        """Process a file input and convert to appropriate Pydantic AI input type
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            Appropriate Pydantic AI input type instance
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        # Determine file type from extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        # Process based on file type
        if ext in self.supported_image_formats:
            return self._process_image(file_path)
        elif ext in self.supported_audio_formats:
            return self._process_audio(file_path)
        elif ext in self.supported_document_formats:
            return self._process_document(file_path)
        elif ext in self.supported_video_formats:
            return self._process_video(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    def process_url_input(self, url: str) -> Union[ImageUrl, VideoUrl, 
                                               DocumentUrl, AudioUrl, None]:
        """Process a URL input and convert to appropriate Pydantic AI input type
        
        Args:
            url: URL string to process
            
        Returns:
            Appropriate Pydantic AI input type instance
        """
        # Check if pydantic-ai is available
        if not PYDANTIC_INPUTS_AVAILABLE:
            raise ImportError("Pydantic AI input types not available")
            
        # Try to determine content type from URL extension
        _, ext = os.path.splitext(url.split('?')[0])  # Remove query params
        ext = ext.lower()
        
        # Process based on apparent content type
        if ext in self.supported_image_formats:
            return ImageUrl(url=url)
        elif ext in self.supported_audio_formats:
            return AudioUrl(url=url)
        elif ext in self.supported_document_formats:
            return DocumentUrl(url=url)
        elif ext in self.supported_video_formats:
            return VideoUrl(url=url)
        else:
            # Default to image URL if we can't determine type
            return ImageUrl(url=url)
    
    def _process_image(self, file_path: str) -> Union[ImageUrl, BinaryContent]:
        """Process an image file"""
        # Check if pydantic-ai is available
        if not PYDANTIC_INPUTS_AVAILABLE:
            raise ImportError("Pydantic AI input types not available")
            
        # Read the file content
        with open(file_path, 'rb') as f:
            content = f.read()
            
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'image/jpeg'  # Default mime type
            
        # Return as binary content
        return BinaryContent(
            content=content,
            media_type=mime_type
        )
    
    def _process_audio(self, file_path: str) -> Union[AudioUrl, BinaryContent]:
        """Process an audio file"""
        # Check if pydantic-ai is available
        if not PYDANTIC_INPUTS_AVAILABLE:
            raise ImportError("Pydantic AI input types not available")
            
        # Read the file content
        with open(file_path, 'rb') as f:
            content = f.read()
            
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'audio/mpeg'  # Default mime type
            
        # Return as binary content
        return BinaryContent(
            content=content,
            media_type=mime_type
        )
    
    def _process_document(self, file_path: str) -> Union[DocumentUrl, BinaryContent]:
        """Process a document file"""
        # Check if pydantic-ai is available
        if not PYDANTIC_INPUTS_AVAILABLE:
            raise ImportError("Pydantic AI input types not available")
            
        # Read the file content
        with open(file_path, 'rb') as f:
            content = f.read()
            
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            # Guess based on extension
            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.pdf':
                mime_type = 'application/pdf'
            elif ext == '.docx':
                mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            else:
                mime_type = 'text/plain'  # Default mime type
            
        # Return as binary content
        return BinaryContent(
            content=content,
            media_type=mime_type
        )
    
    def _process_video(self, file_path: str) -> Union[VideoUrl, BinaryContent]:
        """Process a video file"""
        # Check if pydantic-ai is available
        if not PYDANTIC_INPUTS_AVAILABLE:
            raise ImportError("Pydantic AI input types not available")
            
        # Read the file content
        with open(file_path, 'rb') as f:
            content = f.read()
            
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'video/mp4'  # Default mime type
            
        # Return as binary content
        return BinaryContent(
            content=content,
            media_type=mime_type
        )

class MultimodalInput(BaseModel):
    """Model for multimodal inputs to agents
    
    A Pydantic BaseModel that represents multimodal inputs to be sent to LLMs using Pydantic AI.
    Reference: https://ai.pydantic.dev/types/multimodal/
    """
    text: str = ""
    images: List[Union[ImageUrl, BinaryContent, str]] = Field(default_factory=list)
    audio: List[Union[AudioUrl, BinaryContent, str]] = Field(default_factory=list)
    documents: List[Union[DocumentUrl, BinaryContent, str]] = Field(default_factory=list)
    videos: List[Union[VideoUrl, BinaryContent, str]] = Field(default_factory=list)
    
    def prepare_for_model(self, processor: Optional[InputProcessor] = None) -> Dict[str, Any]:
        """Prepare the input for sending to an LLM model
        
        Args:
            processor: Optional input processor for processing strings
            
        Returns:
            Dictionary representation suitable for model input
        """
        if processor is None:
            processor = InputProcessor()
            
        # Process any string inputs (paths or URLs)
        processed_images = []
        for img in self.images:
            if isinstance(img, str):
                if img.startswith(('http://', 'https://')):
                    processed_images.append(processor.process_url_input(img))
                else:
                    processed_images.append(processor.process_file_input(img))
            else:
                processed_images.append(img)
                
        processed_audio = []
        for aud in self.audio:
            if isinstance(aud, str):
                if aud.startswith(('http://', 'https://')):
                    processed_audio.append(processor.process_url_input(aud))
                else:
                    processed_audio.append(processor.process_file_input(aud))
            else:
                processed_audio.append(aud)
                
        processed_documents = []
        for doc in self.documents:
            if isinstance(doc, str):
                if doc.startswith(('http://', 'https://')):
                    processed_documents.append(processor.process_url_input(doc))
                else:
                    processed_documents.append(processor.process_file_input(doc))
            else:
                processed_documents.append(doc)
                
        processed_videos = []
        for vid in self.videos:
            if isinstance(vid, str):
                if vid.startswith(('http://', 'https://')):
                    processed_videos.append(processor.process_url_input(vid))
                else:
                    processed_videos.append(processor.process_file_input(vid))
            else:
                processed_videos.append(vid)
                
        # Return in the format expected by the model
        return {
            "text": self.text,
            "images": processed_images,
            "audio": processed_audio,
            "documents": processed_documents,
            "videos": processed_videos
        }
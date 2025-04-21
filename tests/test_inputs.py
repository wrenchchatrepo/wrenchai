"""
Tests for the input handling functionality.
"""
import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

from wrenchai.core.inputs import (
    InputProcessor, MultimodalInput, 
    PYDANTIC_INPUTS_AVAILABLE
)

class TestInputs:
    """Tests for the multimodal input handling"""
    
    def setup_method(self):
        """Set up for the tests"""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up after tests"""
        if os.path.exists(self.temp_dir):
            # Remove any test files
            for f in os.listdir(self.temp_dir):
                os.remove(os.path.join(self.temp_dir, f))
            # Remove the directory
            os.rmdir(self.temp_dir)
    
    def create_test_file(self, ext: str, content: bytes = b'test content') -> str:
        """Create a test file with the given extension"""
        file_path = os.path.join(self.temp_dir, f"test_file{ext}")
        with open(file_path, 'wb') as f:
            f.write(content)
        return file_path
    
    def test_process_url_input(self):
        """Test processing URL inputs"""
        if not PYDANTIC_INPUTS_AVAILABLE:
            pytest.skip("Pydantic AI input types not available")
            
        processor = InputProcessor()
        
        # Test image URL
        with patch('wrenchai.core.inputs.ImageUrl') as mock_image_url:
            mock_image_url.return_value = "image_url_instance"
            result = processor.process_url_input("https://example.com/image.jpg")
            assert result == "image_url_instance"
            mock_image_url.assert_called_once()
            
        # Test audio URL
        with patch('wrenchai.core.inputs.AudioUrl') as mock_audio_url:
            mock_audio_url.return_value = "audio_url_instance"
            result = processor.process_url_input("https://example.com/audio.mp3")
            assert result == "audio_url_instance"
            mock_audio_url.assert_called_once()
            
        # Test document URL
        with patch('wrenchai.core.inputs.DocumentUrl') as mock_doc_url:
            mock_doc_url.return_value = "document_url_instance"
            result = processor.process_url_input("https://example.com/doc.pdf")
            assert result == "document_url_instance"
            mock_doc_url.assert_called_once()
            
        # Test video URL
        with patch('wrenchai.core.inputs.VideoUrl') as mock_video_url:
            mock_video_url.return_value = "video_url_instance"
            result = processor.process_url_input("https://example.com/video.mp4")
            assert result == "video_url_instance"
            mock_video_url.assert_called_once()
    
    def test_file_to_binary_content(self):
        """Test converting files to binary content"""
        if not PYDANTIC_INPUTS_AVAILABLE:
            pytest.skip("Pydantic AI input types not available")
            
        processor = InputProcessor()
        
        # Create test files
        image_path = self.create_test_file(".jpg")
        audio_path = self.create_test_file(".mp3")
        document_path = self.create_test_file(".pdf")
        video_path = self.create_test_file(".mp4")
        
        # Test with mocked BinaryContent
        with patch('wrenchai.core.inputs.BinaryContent') as mock_binary:
            mock_binary.return_value = "binary_instance"
            
            # Test image file
            result = processor._process_image(image_path)
            assert result == "binary_instance"
            mock_binary.assert_called_with(content=b'test content', media_type='image/jpeg')
            
            # Test audio file
            result = processor._process_audio(audio_path)
            assert result == "binary_instance"
            mock_binary.assert_called_with(content=b'test content', media_type='audio/mpeg')
            
            # Test document file
            result = processor._process_document(document_path)
            assert result == "binary_instance"
            mock_binary.assert_called_with(content=b'test content', media_type='application/pdf')
            
            # Test video file
            result = processor._process_video(video_path)
            assert result == "binary_instance"
            mock_binary.assert_called_with(content=b'test content', media_type='video/mp4')
    
    def test_multimodal_input_model(self):
        """Test the MultimodalInput model"""
        # Create a multimodal input
        input_data = MultimodalInput(
            text="This is a test query",
            images=["https://example.com/image.jpg"],
            documents=["https://example.com/doc.pdf"]
        )
        
        # Check model structure
        assert input_data.text == "This is a test query"
        assert len(input_data.images) == 1
        assert len(input_data.documents) == 1
        assert len(input_data.audio) == 0
        assert len(input_data.videos) == 0
        
        # Test prepare_for_model with mocked processor
        processor = MagicMock()
        processor.process_url_input.side_effect = lambda url: f"processed_{url}"
        
        prepared = input_data.prepare_for_model(processor)
        
        # Check the prepared output
        assert prepared["text"] == "This is a test query"
        assert prepared["images"] == ["processed_https://example.com/image.jpg"]
        assert prepared["documents"] == ["processed_https://example.com/doc.pdf"]
        assert len(prepared["audio"]) == 0
        assert len(prepared["videos"]) == 0
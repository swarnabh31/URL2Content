import pytest
from unittest.mock import patch, MagicMock
from utils.transcript_extractor import extract_transcript, _extract_video_id

class TestVideoIdExtraction:
    def test_standard_url(self):
        assert _extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    
    def test_short_url(self):
        assert _extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    
    def test_embed_url(self):
        assert _extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    
    def test_invalid_url(self):
        assert _extract_video_id("not-a-url") == ""

class TestTranscriptExtraction:
    @patch('utils.transcript_extractor.YouTubeTranscriptApi')
    def test_successful_extraction(self, mock_api):
        # Mock the transcript API response
        mock_transcript = [
            {'text': 'Hello world', 'start': 0.0, 'duration': 1.0},
            {'text': 'This is a test', 'start': 1.0, 'duration': 2.0}
        ]
        mock_api.get_transcript.return_value = mock_transcript
        
        result = extract_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        
        assert "Hello world" in result
        assert "This is a test" in result
        mock_api.get_transcript.assert_called_once_with("dQw4w9WgXcQ")
    
    @patch('utils.transcript_extractor.YouTubeTranscriptApi')
    def test_extraction_failure(self, mock_api):
        # Mock API failure
        mock_api.get_transcript.side_effect = Exception("Transcript not available")
        
        with pytest.raises(Exception):
            extract_transcript("https://www.youtube.com/watch?v=invalid")
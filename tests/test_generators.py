import pytest
from unittest.mock import patch, MagicMock
from content.generators import summarize_transcript, generate_blog_post, generate_medium_article, generate_linkedin_post

class TestContentGeneration:
    @patch('content.generators._ollama_chat')
    def test_summarize_transcript(self, mock_chat):
        mock_chat.return_value = "# Summary\n\nKey points..."
        result = summarize_transcript("Sample transcript text", "qwen2.5")
        assert "# Summary" in result
        mock_chat.assert_called_once()
    
    @patch('content.generators._ollama_chat')
    def test_generate_blog_post(self, mock_chat):
        mock_chat.return_value = "# Blog Post\n\nIntroduction..."
        result = generate_blog_post("Sample transcript", "Test Title", "llama2")
        assert "# Blog Post" in result
        mock_chat.assert_called_once()
        
    @patch('content.generators._ollama_chat')
    def test_generate_medium_article(self, mock_chat):
        mock_chat.return_value = "# Medium Article\n\nStory..."
        result = generate_medium_article("Sample transcript", "Test Title", "mistral")
        assert "# Medium Article" in result
        mock_chat.assert_called_once()
        
    @patch('content.generators._ollama_chat')
    def test_generate_linkedin_post(self, mock_chat):
        mock_chat.return_value = "Key insights...\n\n💡 Takeaways"
        result = generate_linkedin_post("Sample transcript", "phi3")
        assert "💡 Takeaways" in result
        mock_chat.assert_called_once()
    
    def test_truncation_long_transcript(self):
        # Test that long transcripts are handled gracefully by content processor
        long_text = "x" * 100000
        # This should not crash and should return some processed result
        # We test through the content processor since generators use it
        from content_processor import get_optimal_strategy, ContextStrategy
        strategy = get_optimal_strategy("llama2", len(long_text))
        # For a very long transcript with llama2 (32K context), should be CHUNKED
        assert strategy == ContextStrategy.CHUNKED
"""
ContentGenerators - Generate structured content (Summary, Blog, Article, LinkedIn Post)
from video transcript text using a local Ollama model.
"""

import json
import urllib.request
import urllib.error
import logging
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _ollama_chat(messages: list[dict], model: str) -> str:
    """Send a chat completion request to a local Ollama instance."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": settings.DEFAULT_TEMPERATURE,
            "num_predict": settings.MAX_TOKENS,
        },
    }

    req = urllib.request.Request(
        f"{settings.OLLAMA_BASE_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req, timeout=settings.OLLAMA_TIMEOUT) as resp:
        try:
            result = json.loads(resp.read().decode())
            return result.get("message", {}).get("content", "")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error from Ollama API: {e}")
            return ""


def summarize_transcript(transcript: str, model: str) -> str:
    """Generate a well-structured summary of the transcript."""
    # Truncation is now handled by the content_processor strategy
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert content analyst. Your job is to produce "
                "clear, well-structured summaries of video content. "
                "Use proper markdown formatting with headers, bullet points, and key takeaways. "
                "Be concise but comprehensive. Ready output that can be directly copied and pasted."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Please provide a comprehensive summary of the following video transcript:\n\n"
                f"{'='*60}\n"
                f"{transcript}\n"
                f"{'='*60}\n\n"
                f"Format your summary with:\n"
                f"1. A one-sentence overview at the top\n"
                f"2. Key topics covered (with sub-points)\n"
                f"3. Important quotes or data points\n"
                f"4. Main conclusions or takeaways\n"
                f"5. A brief 'Bottom Line' section\n\n"
                f"Use markdown formatting throughout."
            ),
        },
    ]
    return _ollama_chat(messages, model)


def generate_blog_post(transcript: str, title: str, model: str) -> str:
    """Generate a technical blog post from the transcript."""
    # Truncation is now handled by the content_processor strategy
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert technical writer who writes engaging, "
                "well-structured blog posts for platforms like Substack, Dev.to, or personal blogs. "
                "Your writing is clear, informative, and structured for readability. "
                "Use proper markdown with headers, code blocks if needed, bullet points, and a strong conclusion. "
                "The output should be publication-ready and directly copy-pasteable."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Write a comprehensive technical blog post based on the following video transcript.\n\n"
                f"Title: {title}\n\n"
                f"{'='*60}\n"
                f"{transcript}\n"
                f"{'='*60}\n\n"
                f"Blog post requirements:\n"
                f"- Start with a compelling hook/introduction\n"
                f"- Use H2 headers for major sections\n"
                f"- Break down complex ideas into digestible paragraphs\n"
                f"- Include 3-5 key takeaways as bullet points\n"
                f"- Add a 'Conclusion' section with final thoughts\n"
                f"- Suggest 3-5 'Next Steps' or 'Learn More' items\n"
                f"- Add relevant hashtags at the end (for Dev.to/Substack)\n"
                f"- Keep tone professional yet conversational\n\n"
                f"Write the entire blog post in markdown format."
            ),
        },
    ]
    return _ollama_chat(messages, model)


def generate_medium_article(transcript: str, title: str, model: str) -> str:
    """Generate a Medium-style article from the transcript."""
    # Truncation is now handled by the content_processor strategy
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert writer for Medium. Your articles are thought-provoking, "
                "well-researched, and formatted for the Medium reading experience. "
                "You use storytelling techniques, clear section headers, pull quotes, "
                "and a strong narrative arc. The output should be publication-ready."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Write a Medium-style article based on the following video transcript.\n\n"
                f"Title: {title}\n\n"
                f"{'='*60}\n"
                f"{transcript}\n"
                f"{'='*60}\n\n"
                f"Article requirements:\n"
                f"- Start with a narrative hook that draws the reader in\n"
                f"- Use H2/H3 headers for sections\n"
                f"- Include a brief intro paragraph with context\n"
                f"- Break content into logical sections with clear transitions\n"
                f"- Use 'pull quotes' styled as blockquotes for key insights\n"
                f"- Include a 'What This Means' section analyzing implications\n"
                f"- End with a compelling conclusion and call-to-action\n"
                f"- Add relevant tags at the end (Medium style: 5 tags)\n\n"
                f"Write the entire article in markdown format. Make it engaging and readable."
            ),
        },
    ]
    return _ollama_chat(messages, model)


def generate_linkedin_post(transcript: str, model: str) -> str:
    """Generate a LinkedIn post from the transcript."""
    # Truncation is now handled by the content_processor strategy
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert at crafting viral LinkedIn posts. "
                "You know how to grab attention, tell a story, and deliver value "
                "in a way that resonates with a professional audience. "
                "Your posts use short paragraphs, strategic line breaks, "
                "and a clear hook. Ready to post, directly copy-pasteable."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Write a compelling LinkedIn post based on the key insights from the following video:\n\n"
                f"{'='*60}\n"
                f"{transcript}\n"
                f"{'='*60}\n\n"
                f"LinkedIn post requirements:\n"
                f"- Start with a strong, attention-grabbing hook (first line must stop scrollers)\n"
                f"- Use short paragraphs (1-2 sentences max per paragraph)\n"
                f"- Include 3-5 key lessons/insights\n"
                f"- Add a personal reflection or 'what stood out' section\n"
                f"- End with a question to drive engagement\n"
                f"- Add relevant hashtags (5-7)\n"
                f"- Include a '💡 Key Takeaways' section with bullet points\n\n"
                f"Write in first person. Make it authentic, not clickbait. "
                f"Format with proper line breaks for LinkedIn."
            ),
        },
    ]
    return _ollama_chat(messages, model)

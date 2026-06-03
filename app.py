"""
Main Streamlit Application - YouTube to Content Creator
"""

import streamlit as st
import re
import logging
import time
from datetime import datetime
from utils.cache_manager import CacheManager
from utils.session_manager import JobQueue
from logging_config import setup_logging
from config import get_settings
from error_handler import handle_error, AppError
from content_processor import get_optimal_strategy, ContextStrategy, smart_truncate, chunk_transcript
from utils.ollama_manager import get_text_chat_models, get_model_names, is_ollama_available
from utils.transcript_extractor import extract_transcript
from content.generators import summarize_transcript, generate_blog_post, generate_medium_article, generate_linkedin_post
from validators import validate_youtube_url, sanitize_transcript
from history_manager import HistoryManager
from pdf_generator import generate_pdf

# Initialize Logging
setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()
cache = CacheManager()
history_manager = HistoryManager()

# Initialize JobQueue in session state to persist across reruns
if "job_queue" not in st.session_state:
    st.session_state["job_queue"] = JobQueue(max_concurrent=1)
queue = st.session_state["job_queue"]


# ============================================================
# PDF Generator (markdown -> PDF via fpdf2)
# ============================================================

def execute_generation_job(job_id, jq, transcript_text, selected_model, selected_type, title):
    """
    Workload function executed by the JobQueue thread.
    """
    try:
        jq.update_progress(job_id, 0.1)
        
        # 1. Context Processing
        strategy = get_optimal_strategy(selected_model, len(transcript_text))
        jq.update_progress(job_id, 0.3)
        
        if strategy == ContextStrategy.FULL:
            processed_text = transcript_text
        elif strategy == ContextStrategy.SMART:
            processed_text = smart_truncate(transcript_text)
        elif strategy == ContextStrategy.CHUNKED:
            chunks = chunk_transcript(transcript_text)
            chunk_summaries = []
            for i, chunk in enumerate(chunks):
                chunk_summaries.append(f"## Section {i+1}\\n{summarize_transcript(chunk, selected_model)}")
                jq.update_progress(job_id, 0.3 + (0.4 * (i+1)/len(chunks)))
            processed_text = "\\n\\n".join(chunk_summaries)
        
        # 2. Final Generation
        jq.update_progress(job_id, 0.8)
        if selected_type == "Summary":
            output = summarize_transcript(processed_text, selected_model)
        elif selected_type == "Technical Blog Post":
            output = generate_blog_post(processed_text, title or "Untitled", selected_model)
        elif selected_type == "Medium Article":
            output = generate_medium_article(processed_text, title or "Untitled", selected_model)
        elif selected_type == "LinkedIn Post":
            output = generate_linkedin_post(processed_text, selected_model)
        else:
            output = "Unsupported content type"
            
        jq.update_progress(job_id, 1.0)
        return output
    except Exception as e:
        logger.error(f"Job {job_id} failed during execution: {e}")
        raise e

def _strip_non_ascii(text: str) -> str:
    """Remove all characters outside the ASCII printable range (32-126) plus basic whitespace."""
    result = []
    for ch in text:
        code = ord(ch)
        if 32 <= code <= 126 or ch in "\n\r\t":
            result.append(ch)
    return ''.join(result)


def _parse_inline_formatting(text: str) -> list:
    """Parse inline markdown (bold ** **, italic * *) into segments.
    Returns list of (text, style) tuples."""
    segments = []
    current_text = []
    current_style = 'normal'
    i = 0
    while i < len(text):
        # Bold: **text**
        if i + 1 < len(text) and text[i] == '*' and text[i+1] == '*':
            if current_style == 'bold':
                if current_text:
                    segments.append((''.join(current_text), 'bold'))
                    current_text = []
                current_style = 'normal'
                i += 2
                continue
            else:
                if current_text:
                    segments.append((''.join(current_text), current_style))
                    current_text = []
                current_style = 'bold'
                i += 2
                continue
        # Italic: single * (not part of **)
        if text[i] == '*':
            if (i > 0 and text[i-1] == '*') or (i + 1 < len(text) and text[i+1] == '*'):
                i += 1
                continue
            if current_style == 'italic':
                if current_text:
                    segments.append((''.join(current_text), 'italic'))
                    current_text = []
                current_style = 'normal'
                i += 1
                continue
            else:
                if current_text:
                    segments.append((''.join(current_text), current_style))
                    current_text = []
                current_style = 'italic'
                i += 1
                continue
        current_text.append(text[i])
        i += 1
    if current_text:
        segments.append((''.join(current_text), current_style))
    return segments if segments else [('', 'normal')]


def _render_styled_text(pdf, segments, x, y, font_size, max_width):
    """Render text with inline formatting, word-wrapping to fit max_width."""
    current_y = y
    line_height = font_size * 0.45
    for text_part, style in segments:
        if not text_part:
            continue
        if style == 'bold':
            pdf.set_font('Helvetica', 'B', font_size)
        elif style == 'italic':
            pdf.set_font('Helvetica', 'I', font_size)
        else:
            pdf.set_font('Helvetica', '', font_size)
        words = text_part.split()
        if not words:
            continue
        current_line = []
        line_width = 0
        for word in words:
            word_width = pdf.get_string_width(word + ' ')
            if line_width + word_width > max_width and current_line:
                line_text = ' '.join(current_line)
                pdf.set_xy(x, current_y)
                pdf.multi_cell(max_width, line_height, line_text, new_x='LMARGIN', new_y='NEXT')
                current_y = pdf.get_y()
                line_width = 0
                current_line = []
            current_line.append(word)
            line_width += word_width + pdf.get_string_width(' ')
        if current_line:
            line_text = ' '.join(current_line)
            pdf.set_xy(x, current_y)
            pdf.multi_cell(max_width, line_height, line_text, new_x='LMARGIN', new_y='NEXT')
            current_y = pdf.get_y()
    return current_y


def _generate_pdf(markdown_text: str) -> bytes | None:
    """Convert markdown content to PDF using the professional PDF generator."""
    try:
        # Use our new professional PDF generator
        pdf_data = generate_pdf(markdown_text, "YouTube Content")
        return pdf_data if pdf_data else None
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        return None


def _parse_markdown_to_blocks(text: str) -> list:
    """Parse markdown into structured blocks for PDF rendering."""
    blocks = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        # Code block
        if line.strip().startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append({"type": "code", "text": "\n".join(code_lines)})
            i += 1
            continue
        # Horizontal rule
        if line.strip() in ("---", "***", "___"):
            blocks.append({"type": "hr"})
            i += 1
            continue
        # Headings
        if line.startswith("### "):
            blocks.append({"type": "h3", "text": line[4:].strip()})
            i += 1
            continue
        if line.startswith("## "):
            blocks.append({"type": "h2", "text": line[3:].strip()})
            i += 1
            continue
        if line.startswith("# "):
            blocks.append({"type": "h1", "text": line[2:].strip()})
            i += 1
            continue
        # Blockquote
        if line.startswith("> "):
            quote_lines = []
            while i < len(lines) and lines[i].startswith("> "):
                quote_lines.append(lines[i][2:])
                i += 1
            blocks.append({"type": "quote", "text": " ".join(quote_lines)})
            continue
        # Unordered list
        if re.match(r'^[-*]\s+', line):
            items = []
            while i < len(lines) and re.match(r'^[-*]\s+', lines[i]):
                items.append(re.sub(r'^[-*]\s+', '', lines[i]))
                i += 1
            blocks.append({"type": "list", "items": items})
            continue
        # Ordered list
        if re.match(r'^\d+\.\s+', line):
            items = []
            while i < len(lines) and re.match(r'^\d+\.\s+', lines[i]):
                items.append(re.sub(r'^\d+\.\s+', '', lines[i]))
                i += 1
            blocks.append({"type": "list", "items": items})
            continue
        # Paragraph
        para_lines = []
        while i < len(lines) and lines[i].strip():
            para_lines.append(lines[i].strip())
            i += 1
        if para_lines:
            blocks.append({"type": "p", "text": " ".join(para_lines)})
        i += 1
    return blocks


# ============================================================
# Page Config
# ============================================================

st.set_page_config(
    page_title="YouTube to Content Creator",
    page_icon=":video_camera:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("YouTube to Content Creator")
st.markdown("*Extract transcripts from any YouTube video and generate professional content with your local Ollama models.*")
st.markdown("---")

# ============================================================
# Sidebar: Model Selection
# ============================================================

with st.sidebar:
    st.header("Settings")

    # Ollama status
    if is_ollama_available():
        st.success("Ollama is running")
        ollama_status = True
    else:
        st.warning("Ollama not found")
        st.info("Make sure Ollama is running locally: `ollama serve`")
        ollama_status = False

    # Model selection
    if ollama_status:
        available_models = get_model_names()
        if not available_models:
            st.warning("No text/chat models found. Run `ollama pull <model>` to download one.")
        else:
            st.subheader("Ollama Model")
            st.info(f"{len(available_models)} model(s) detected")
            selected_model = st.selectbox(
                "Choose a model",
                available_models,
                index=0,
                help="Select the local Ollama model to use for content generation.",
            )
    else:
        selected_model = None

    st.divider()
    st.markdown("""
    ### How to Use
    1. Paste a YouTube URL
    2. Extract the transcript
    3. Choose content type
    4. Generate and copy your content!
    """)

# ============================================================
# Main Content
# ============================================================

# Step 1: URL Input
st.header("Step 1: Paste YouTube URL")
youtube_url = st.text_input(
    "YouTube Video URL",
    placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    help="Paste the full YouTube URL of the video you want to convert.",
)

# Reset content when a new URL is pasted
if "last_url" not in st.session_state:
    st.session_state["last_url"] = ""

if youtube_url != st.session_state["last_url"]:
    st.session_state["last_url"] = youtube_url
    # Clear previous results when URL changes
    if "generated_content" in st.session_state:
        del st.session_state["generated_content"]
    if "content_type" in st.session_state:
        del st.session_state["content_type"]
    if "active_job_id" in st.session_state:
        del st.session_state["active_job_id"]
    # Note: We keep the transcript in session_state until the new Extract button is pressed
    # to avoid flashing, but we clear the lapped output.

# Step 2: Transcript Extraction
st.header("Step 2: Extract Transcript")
extract_btn = st.button("Extract Transcript", type="primary", disabled=not youtube_url)

if extract_btn and youtube_url:
    with st.spinner("Extracting transcript... This may take a moment."):
        try:
            # Validate YouTube URL
            video_id = validate_youtube_url(youtube_url)
            
            # --- CACHE CHECK ---
            cached_transcript = cache.get_transcript(youtube_url)
            if cached_transcript:
                transcript = cached_transcript
                st.info("Loaded transcript from cache ⚡")
            else:
                transcript = extract_transcript(youtube_url)
                # Sanitize transcript to prevent prompt injection
                transcript = sanitize_transcript(transcript)
                cache.save_transcript(youtube_url, transcript)
            
            if len(transcript) < 50:
                st.error("Transcript seems too short. The video may not have captions.")
            else:
                st.success(f"Transcript extracted! ({len(transcript):,} characters)")
                st.session_state["transcript"] = transcript
                st.session_state["url"] = youtube_url

                # Show transcript preview
                with st.expander("View Transcript (first 2000 chars)"):
                    st.code(transcript[:2000], language=None)
                if len(transcript) > 2000:
                    st.caption(f"... and {len(transcript) - 2000} more characters")
                
                # Transcript download options
                st.markdown("**Download Transcript**")
                col1, col2 = st.columns(2)
                
                with col1:
                    # Plain text download (without timestamps)
                    st.download_button(
                        label="Download as .txt",
                        data=transcript,
                        file_name=f"transcript_{st.session_state.get('url', 'video').replace('https://', '').replace('http://', '').replace('/', '_').replace(':', '_').strip('_')}.txt",
                        mime="text/plain",
                    )
                
                with col2:
                    # For now, we'll provide the same transcript since we don't have timestamp data
                    # In a future enhancement, we could provide SRT/VTT format with timestamps
                    st.download_button(
                        label="Download with Timestamps (.txt)",
                        data=transcript,  # Same content for now
                        file_name=f"transcript_with_timestamps_{st.session_state.get('url', 'video').replace('https://', '').replace('http://', '').replace('/', '_').replace(':', '_').strip('_')}.txt",
                        mime="text/plain",
                        help="Timestamp data would be included if available from the source"
                    )
        except Exception as e:
            st.error(f"Failed to extract transcript: {e}")

# Step 3: Content Generation
if "transcript" in st.session_state:
    st.header("Step 3: Generate Content")
    
    content_types = [
        ("Summary", "summary"),
        ("Technical Blog Post", "blog"),
        ("Medium Article", "medium"),
        ("LinkedIn Post", "linkedin"),
    ]
    
    selected_type = st.radio(
        "Choose content type",
        [t[0] for t in content_types],
        horizontal=True,
        help="Select what kind of content you want to generate.",
    )
    
    # Blog/Medium may need a title
    if selected_type in ["Technical Blog Post", "Medium Article"]:
        title = st.text_input(
            "Content Title (optional)",
            placeholder="My Awesome Blog Post Title",
            help="Leave blank to auto-generate a title from the content.",
        )
        if not title:
            title = None
    else:
        title = None
    
    generate_btn = st.button("Generate Content", type="primary", disabled=not selected_model)
    
    if generate_btn and selected_model:
        with st.spinner(f"Queuing {selected_type} with {selected_model}..."):
            try:
                # --- CACHE CHECK ---
                transcript_text = st.session_state["transcript"]
                cached_content = cache.get_content(transcript_text, selected_model, selected_type)
                
                if cached_content:
                    output = cached_content
                    st.info("Loaded content from cache ⚡")
                    st.session_state["generated_content"] = output
                    st.session_state["content_type"] = selected_type
                    # Save to history
                    history_manager.save(
                        url=st.session_state.get("url", "unknown"),
                        content_type=selected_type,
                        model=selected_model,
                        content=output,
                        transcript_len=len(transcript_text),
                        duration_ms=0  # Cached content has no generation time
                    )
                else:
                    # Ensure title is defined even if it's not used for the selected type
                    current_title = title if 'title' in locals() else None
                    
                    # --- QUEUE SUBMISSION ---
                    # We create a closure for the job function to capture current parameters
                    def job_wrapper(job_id, jq):
                        # Update progress through the queue (thread-safe)
                        jq.update_progress(job_id, 0.1)
                        
                        # 1. Context Processing
                        strategy = get_optimal_strategy(selected_model, len(transcript_text))
                        jq.update_progress(job_id, 0.3)
                        
                        if strategy == ContextStrategy.FULL:
                            processed_text = transcript_text
                        elif strategy == ContextStrategy.SMART:
                            processed_text = smart_truncate(transcript_text)
                        elif strategy == ContextStrategy.CHUNKED:
                            chunks = chunk_transcript(transcript_text)
                            chunk_summaries = []
                            for i, chunk in enumerate(chunks):
                                chunk_summaries.append(f"## Section {i+1}\\n{summarize_transcript(chunk, selected_model)}")
                                jq.update_progress(job_id, 0.3 + (0.4 * (i+1)/len(chunks)))
                            processed_text = "\\n\\n".join(chunk_summaries)
                        
                        # 2. Final Generation
                        jq.update_progress(job_id, 0.8)
                        if selected_type == "Summary":
                            output = summarize_transcript(processed_text, selected_model)
                        elif selected_type == "Technical Blog Post":
                            output = generate_blog_post(processed_text, title or "Untitled", selected_model)
                        elif selected_type == "Medium Article":
                            output = generate_medium_article(processed_text, title or "Untitled", selected_model)
                        elif selected_type == "LinkedIn Post":
                            output = generate_linkedin_post(processed_text, selected_model)
                        else:
                            output = "Unsupported content type"
                            
                        jq.update_progress(job_id, 1.0)
                        return output
                    
                    job_id = queue.submit(
                        url=st.session_state.get("url", "unknown"),
                        content_type=selected_type,
                        model=selected_model,
                        processing_func=job_wrapper
                    )
                    st.session_state["active_job_id"] = job_id
                    st.info(f"Job submitted! ID: {job_id}. Processing in background... ⏳")
            except Exception as e:
                logger.error(f"Queue submission failed: {e}", exc_info=True)
                st.error(f"Failed to queue content: {e}")

# Step 4: Display & Copy Generated Content
if "generated_content" in st.session_state or "active_job_id" in st.session_state:
    st.header("Step 4: Your Content & Status")

    # Check for background job status
    if "active_job_id" in st.session_state:
        job_id = st.session_state["active_job_id"]
        job = queue.get_job_status(job_id)
        
        if job:
            if job.status == "running":
                st.info(f"Job Status: Running | Progress: {job.progress*100:.1f}%")
                st.progress(job.progress)
                time.sleep(1)
                st.rerun()
            
            elif job.status == "queued":
                st.info(f"Job Status: Queued... waiting for GPU ⏳")
                time.sleep(1)
                st.rerun()
            
            elif job.status == "completed":
                st.success("Generation Complete! ⚡")
                st.session_state["generated_content"] = job.result
                st.session_state["content_type"] = job.content_type
                # Save to history
                history_manager.save(
                    url=job.url,
                    content_type=job.content_type,
                    model=job.model,
                    content=job.result,
                    transcript_len=len(st.session_state.get("transcript", "")),
                    duration_ms=int((job.progress or 1.0) * 30000)  # Approximate time
                )
                del st.session_state["active_job_id"]
                st.rerun()
                
            elif job.status == "failed":
                st.error(f"Job failed: {job.error}")
                # We keep the job_id for a moment so the user can see the error
                # But we provide a button to clear it
                if st.button("Clear Error & Reset"):
                    del st.session_state["active_job_id"]
                    st.rerun()
        else:
            # Job not found in queue (shouldn't happen)
            del st.session_state["active_job_id"]

    if "generated_content" in st.session_state:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(st.session_state["generated_content"])

        with col2:
            st.markdown("**Download**")
            raw_content = st.session_state["generated_content"]
            url_type = st.session_state.get("url", "video")
            # Derive a safe filename from the URL
            safe_name = url_type.replace("http://", "").replace("https://", "").replace("/", "_").replace(":", "_").strip("_")

            # Markdown download
            st.download_button(
                label="Download as .md",
                data=raw_content,
                file_name=f"{safe_name}_content.md",
                mime="text/markdown",
            )

            # Plain text download
            st.download_button(
                label="Download as .txt",
                data=raw_content,
                file_name=f"{safe_name}_content.txt",
                mime="text/plain",
            )

            st.divider()

            # PDF download
            pdf_data = _generate_pdf(raw_content)
            if pdf_data:
                st.download_button(
                    label="Download as .pdf",
                    data=pdf_data,
                    file_name=f"{safe_name}_content.pdf",
                    mime="application/pdf",
                )
            else:
                st.caption("PDF generation unavailable")

            st.divider()
            st.markdown("**Copy**")
            st.code(raw_content, language="markdown")

# ============================================================
# Footer
# ============================================================
st.markdown("---")
st.caption(
    "Built with Streamlit, yt-dlp, youtube-transcript-api, and Ollama. "
    "All content generation runs locally on your machine."
)

# 🎬 YouTube → Content Creator

Transform any YouTube video into professional content — instantly. Powered by **Streamlit** and **Ollama** for fully local, private AI generation.

## ✨ Features

- 📥 **Transcript Extraction** — Pull captions/subtitles from any YouTube video, download with or without timestamps
- 🤖 **Local LLM Generation** — Uses your installed Ollama models (no API keys, no cloud)
- 📝 **Summary** — Quick, structured overviews of video content
- 📰 **Technical Blog** — Publication-ready Dev.to / Substack blog posts
- ✍️ **Medium Article** — Engaging Medium-style articles with storytelling
- 💼 **LinkedIn Post** — Scroll-stopping professional posts
- 🔒 **100% Private** — Everything runs on your machine
- 📥 **One-Click Copy / Download** — Content ready to paste anywhere
- 📄 **Transcript Download** — Extract and download video transcripts with or without timestamps

## 🚀 Quick Start

### Prerequisites

1. **Python 3.10+** installed
2. **Ollama** installed and running — [ollama.ai](https://ollama.ai)
3. At least one text/chat model pulled locally:
   ```bash
   ollama pull qwen2.5
   # or
   ollama pull phi3
   # or
   ollama pull llama3.2

## Installation

# Clone the repository
git clone https://github.com/YOUR_USERNAME/content-creator.git
cd content-creator

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
The app will open in your browser at http://localhost:8501.

# 📋 How to Use
Paste a YouTube URL — Any YouTube video link
Extract Transcript — Click to pull captions
Choose a Model — Select from the sidebar dropdown (auto-detected)
Select Content Type — Summary, Blog, Article, or LinkedIn
Generate — Click to create your content
Copy or Download — Copy-paste directly or download as .md

# 🏗️ Project Structure

content-creator/

├── app.py                  # Main Streamlit application

├── content/

│   ├── __init__.py

│   └── generators.py       # Content generation logic (summary, blog, etc.)

├── utils/

│   ├── __init__.py

│   ├── ollama_manager.py   # Ollama model detection & filtering

│   └── transcript_extractor.py  # YouTube transcript extraction

├── requirements.txt        # Python dependencies

├── .env.example            # Environment variable template

├── .gitignore

├── README.md

└── LICENSE

🤝 Supported Content Types
# Type	Description
- 📝 Summary	Structured overview with key topics, quotes & takeaways
- 📰 Technical Blog	Full blog post with sections, takeaways & hashtags
- ✍️ Medium Article	Story-driven article with pull quotes & tags
- 💼 LinkedIn Post	Scroll-stopping professional post with engagement hooks
- ⚙️ Configuration
# Variable	Default	Description
- OLLAMA_BASE_URL	http://localhost:11434	Ollama API endpoint
- STREAMLIT_SERVER_PORT	8501	Streamlit server port
- Create a .env file from .env.example to override defaults.

# 🛠️ Tech Stack
- Frontend: Streamlit
- Transcript: yt-dlp, youtube-transcript-api
- AI: Ollama (local inference)
- Language: Python 3.10+

# 📄 License
MIT License — see LICENSE for details.

# 🙏 Acknowledgments
- yt-dlp — YouTube downloader
- youtube-transcript-api — Transcript extraction
- Ollama — Local AI inference
-Streamlit — App framework


Built with ❤️ for creators who value privacy and local AI.

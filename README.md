<h2 align="center">
 <br>
 <img src="https://search.brave.com/images?q=voice+png&context=W3sic3JjIjoiaHR0cHM6Ly9jZG4uaWNvbnNjb3V0LmNvbS9pY29uL3ByZW1pdW0vcG5nLTI1Ni10aHVtYi9taWMtaWNvbi1zdmctZG93bmxvYWQtcG5nLTgyOTgyNDYucG5nP2Y9d2VicCZ3PTEyOCIsInRleHQiOiJNaWMgTWljcm9waG9uZSBWb2ljZSBJY29uIiwicGFnZV91cmwiOiJodHRwczovL2ljb25zY291dC5jb20vaWNvbnMvZ29vZ2xlLXZvaWNlIn1d&sig=70a9461ab71e9fa852609fc02c97fb98753bbfa1bd7702aa7f7d0cfdb17426d5&nonce=fb78d1712c09a0b6d59c31841df956b9&source=imageCluster" alt="Generate Organized Notes with EchoMind" width="150">
 <br>
 <br>
 EchoMind: Generate organized notes from audio 
 <br>
</h2>

 

<p align="center">
 <a href="#Overview">Overview</a> •
 <a href="#Features">Features</a> •
 <a href="#Quickstart">Quickstart</a> •
 <a href="#Contributing">Contributing</a>
</p>

<br>

## Overview

**EchoMind** is an intelligent streamlit application that transforms audio lectures into well-structured, comprehensive notes. Built with Groq's Whisper API for transcription and Llama models for content generation, EchoMind scaffolds the creation of structured lecture notes by iteratively structuring and generating notes from transcribed audio lectures.

The application strategically uses **Llama 4 Maverick** for generating the notes structure and **Llama 4 Scout** for creating the detailed content, balancing speed and quality for optimal results.

### Features

- 🎧 **Generate Structured Notes** - Transform audio lectures into comprehensive, well-organized notes using Whisper-large transcription and Llama content generation
- ⚡ **Lightning Fast Processing** - Ultra-fast transcription and text generation powered by Groq's infrastructure
- 📖 **Intelligent Scaffolding** - Strategically switches between Llama 4 Maverick and Llama 4 Scout to balance speed and quality
- 🖊️ **Visual Enhancements** - Beautiful markdown styling with contextual icons/emojis for different section types:
  - 📋 Introduction/Overview
  - 💡 Concepts/Theories
  - 📝 Examples/Applications
  - 🎯 Conclusions
  - 🔬 Methods/Techniques
  - 📊 Results/Findings
- 🔊 **Text-to-Speech (TTS)** - Listen to your generated notes using browser-based Web Speech API
- 🎤 **Real-Time Audio Recording** - Record audio directly in the browser for immediate processing
- 👥 **Speaker Identification** - Automatically identifies and analyzes speakers in conversations
- 📂 **Multiple Export Options** - Download notes as text files or beautifully formatted PDFs with EchoMind branding
- 🎨 **Modern UI** - Cream and black theme with enhanced visual hierarchy and user-friendly interface

                                     |

> As with all generative AI, content may include inaccurate or placeholder information. EchoMind is in beta and all feedback is welcome!

---

## Quickstart

> [!IMPORTANT]
> To use EchoMind, you can run it locally with Streamlit using the quickstart instructions below.

### Run locally:

#### Step 1: Set Up Environment Variables

Create a `.env` file in the project root based on `example.env`:

```env
GROQ_API_KEY=your_groq_key_here
AZURE_SPEECH_KEY=your_azure_key_here (optional)
AZURE_REGION=your_azure_region (optional)
GEMINI_API_KEY=your_gemini_key_here (optional)
```

**Required:**
- `GROQ_API_KEY` - Required for transcription and note generation

**Optional:**
- `AZURE_SPEECH_KEY` & `AZURE_REGION` - For enhanced Azure TTS (fallback to browser TTS available)
- `GEMINI_API_KEY` - For future Gemini integration

Alternatively, you can set your Groq API key in environment variables:

```bash
export GROQ_API_KEY="gsk_yA..."
```

#### Step 2: Set Up Virtual Environment

Create and activate a virtual environment:

```bash
python3 -m venv venv
```

**On Windows:**
```bash
venv\Scripts\activate
```

**On macOS/Linux:**
```bash
source venv/bin/activate
```

#### Step 3: Install Dependencies

```bash
pip3 install -r requirements.txt
```

**Note:** For PDF generation on Linux/Mac, additional system libraries may be required. On Windows, PDF generation may not be available without additional setup (text export is always available).

#### Step 4: Run the Application

**Option A: Run directly with Streamlit**
```bash
streamlit run main.py
```

**Option B: Run with Docker (Recommended for production)**
```bash
# Using Docker Compose
docker-compose up -d

# Or using Docker directly
docker build -t echomind:latest .
docker run -d -p 8501:8501 -e GROQ_API_KEY=your_key_here echomind:latest
```

The application will open in your default web browser at `http://localhost:8501`.

For detailed Docker setup instructions, see [DOCKER_SETUP.md](DOCKER_SETUP.md).

## Usage

### Input Methods

EchoMind supports three ways to input audio:

1. **Upload Audio File** - Upload MP3, WAV, or M4A files directly
2. **YouTube Link** - Provide a YouTube URL to download and process audio
3. **Live Recording** - Record audio directly in the browser using the built-in recorder

### Generating Notes

1. Choose your input method (upload, YouTube link, or record)
2. Click **"Generate Notes"** to start processing
3. Watch as EchoMind:
   - Transcribes the audio using Whisper-large
   - Identifies speakers (if multiple speakers detected)
   - Generates a structured outline
   - Creates comprehensive content for each section
4. View your notes with enhanced visual formatting and icons

### Listening to Notes

After notes are generated, use the **"Listen Notes (AI Voice)"** button to hear your notes read aloud using browser-based text-to-speech.

### Downloading Notes

Click **"End Generation and Download Notes"** to download your notes as:
- **Text File** (.txt) - Plain text format with markdown
- **PDF File** (.pdf) - Beautifully formatted PDF with EchoMind branding (if available on your system)

## Details

### Technologies

- **Streamlit** - Web application framework
- **Groq Cloud** - High-performance inference platform
  - **Llama 4 Maverick** - For generating notes structure
  - **Llama 4 Scout** - For generating detailed content
  - **Whisper-large-v3** - For audio transcription
- **Python-dotenv** - Environment variable management
- **md2pdf** - PDF generation from markdown (optional)
- **yt-dlp** - YouTube video/audio downloading
- **Azure Speech SDK** - Enhanced TTS support (optional)

### Architecture

EchoMind uses a two-stage generation process:

1. **Structure Generation** - Uses Llama 4 Maverick to analyze the transcript and create a comprehensive outline
2. **Content Generation** - Uses Llama 4 Scout to generate detailed content for each section in the outline

This approach balances quality (from the larger Maverick model) with speed (from the faster Scout model).

### Limitations

- EchoMind may generate inaccurate information or placeholder content. It should be used as a study aid and all generated content should be reviewed.
- PDF generation requires system libraries and may not work on all Windows systems without additional setup.
- Audio files larger than 100 MB may not be processed due to API limitations.
- Browser-based TTS quality depends on your browser's implementation.

## Project Information

**EchoMind** was created as a Major Project by:

- **Created by:** Pratik Dalvi, Sushant Marathe, Abhinav Anand, Sushmita Shinde
- **Mentor:** Prof. Dr. Manisha Ghalphade
- **Major Project Group:** LYCORE610
- **Institution:** School of Computing, MIT ADT University, Pune
- **Year:** 2025

## Contributing

Improvements through PRs are welcome! Please ensure your contributions:

- Maintain backward compatibility
- Include proper error handling
- Follow the existing code style
- Update documentation as needed

## Changelog

### v2.0.0 - EchoMind Upgrade

 
- 🎨 **Visual Enhancements** - Added contextual icons and enhanced formatting for notes
- 🔊 **Text-to-Speech** - Browser-based TTS for listening to generated notes
- 🎤 **Real-Time Recording** - Live audio recording directly in browser
- 👥 **Speaker Identification** - Automatic speaker detection and analysis
- 📄 **Enhanced PDF Export** - Improved PDF generation 
- 🔒 **Secure API Key Handling** - All keys stored in `.env` file
- 📋 **Professional Footer** - Added creator information and institution details

### v0.1.0 - Initial Release

Initial release of the application codebase with core features:

- 🎧 Generate structured notes using transcribed audio by Whisper-large and text by Llama
- ⚡ Lightning fast speed transcribing audio and generating text using Groq
- 📖 Scaffolded prompting strategically switches between Llama 4 Maverick and Llama 4 Scout
- 🖊️ Markdown styling creates aesthetic notes on the streamlit app
- 📂 Allows user to download a text or PDF file with the entire notes contents

### Future Features:

- Create summary version of transcript, batching into sections of n characters
- Allow upload of multiple audio files
- Azure Speech SDK integration for higher quality TTS
- Progress bars for long operations
- History of generated notes
- Export to .docx format
- Light/dark theme toggle

---

**EchoMind © 2025** - Intelligent note generation powered by AI



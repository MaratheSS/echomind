import streamlit as st
from groq import Groq
import json
import os
from io import BytesIO
from dotenv import load_dotenv
from download import download_video_audio, delete_download, MAX_FILE_SIZE, FILE_TOO_LARGE_MESSAGE
import base64
import time
import sqlite3
from datetime import datetime

# Add these lines after your existing imports at the top
from email_service import EmailService
from sentiment_analysis import (
    analyze_sentiment_with_groq, analyze_sentiment_basic,
    render_sentiment_display
)
from quiz_generator import generate_quiz, render_quiz
from flashcard_generator import generate_flashcards, render_flashcards

# Initialize email service (add after load_dotenv section)
email_service = EmailService()

# Supported languages for transcription (add as a constant)
SUPPORTED_LANGUAGES = {
    "Auto Detect": "auto",
    "English": "en",
    "Hindi": "hi",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Japanese": "ja",
    "Korean": "ko",
    "Chinese": "zh",
    "Arabic": "ar",
    "Portuguese": "pt",
    "Russian": "ru",
    "Italian": "it",
    "Marathi": "mr",
    "Tamil": "ta",
    "Telugu": "te",
    "Bengali": "bn",
}

# Flowchart generation is now powered by Mermaid (built into Streamlit)
FLOWCHART_AVAILABLE = True
nx = None
plt = None

# Try to import md2pdf, but make it optional for Windows compatibility
try:
    from md2pdf.core import md2pdf
    MD2PDF_AVAILABLE = True
except (ImportError, OSError) as e:
    MD2PDF_AVAILABLE = False
    md2pdf = None

# Try to import fpdf2 as fallback PDF generator (works better on Windows)
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    FPDF = None

# PDF is available if either library is available
PDF_AVAILABLE = MD2PDF_AVAILABLE or FPDF_AVAILABLE

# Try to import Azure Speech SDK (optional)
try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_SPEECH_AVAILABLE = True
except ImportError:
    AZURE_SPEECH_AVAILABLE = False
    speechsdk = None

# Load environment variables - try .env first, then example.env as fallback
if os.path.exists('.env'):
    load_dotenv('.env')
else:
    load_dotenv('example.env')

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", None)
AZURE_SPEECH_KEY = os.environ.get("AZURE_SPEECH_KEY", None)
AZURE_REGION = os.environ.get("AZURE_REGION", None)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", None)
audio_file_path = None
uploaded_filename = None

if 'api_key' not in st.session_state:
    st.session_state.api_key = GROQ_API_KEY

if 'groq' not in st.session_state:
    if GROQ_API_KEY:
        st.session_state.groq = Groq()

st.set_page_config(
    page_title="EchoMind",
    page_icon="🧠",
    layout="wide",
)

# Authentication logic
import auth
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    auth.init_user_db()
    
    # Optional centered layout for login page
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        auth.show_login_page()
    st.stop()  # Stop rendering the rest of the application until authenticated


# Apply FreeCodeCamp Inspired Theme
st.markdown("""
<style>
    /* FreeCodeCamp Inspired Theme */
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&family=Lato:wght@400;700&display=swap');

    :root {
        --bg-color: #0a0a23;
        --secondary-bg: #1b1b32;
        --border-color: #3b3b4f;
        --text-color: #ffffff;
        --text-muted: #d0d0e5;
        --primary-green: #198754;
        --primary-green-hover: #006400;
        --accent-yellow: #fecc4c;
    }
    
    html, body, [class*="css"] {
        font-family: 'Lato', sans-serif !important;
        color: var(--text-color) !important;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Lato', sans-serif !important;
        font-weight: 700 !important;
        color: var(--text-color) !important;
        border-bottom: 2px solid var(--border-color);
        padding-bottom: 10px;
        margin-bottom: 20px;
    }

    /* Main background */
    .stApp {
        background-color: var(--bg-color) !important;
    }
    
    /* Main content area */
    .main .block-container {
        max-width: 900px;
        background-color: var(--bg-color);
        padding: 40px;
        margin: auto;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: var(--secondary-bg) !important;
        border-right: 1px solid var(--border-color);
    }
    
    /* Buttons */
    .stButton > button {
        background-color: var(--primary-green) !important;
        color: white !important;
        border: 1px solid var(--primary-green) !important;
        border-radius: 0px !important; /* FCC uses sharp corners often */
        font-weight: 600 !important;
        padding: 10px 20px !important;
        transition: background-color 0.2s ease;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stButton > button:hover {
        background-color: var(--primary-green-hover) !important;
        border-color: var(--primary-green-hover) !important;
    }
    
    /* Inputs */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stTextArea > div > div > textarea {
        background-color: var(--secondary-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 0px !important;
        color: var(--text-color) !important;
    }
    
    /* Info panels */
    .stInfo, .stSuccess, .stError, .stWarning {
        background-color: var(--secondary-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-left: 5px solid var(--primary-green) !important;
        color: var(--text-color) !important;
        border-radius: 0px !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: var(--secondary-bg) !important;
        border-bottom: 1px solid var(--border-color);
    }
    .stTabs [data-baseweb="tab"] {
        color: var(--text-muted) !important;
        background-color: transparent !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--text-color) !important;
        border-bottom: 3px solid var(--primary-green) !important;
    }

    /* Code Blocks */
    code {
        font-family: 'Fira Code', monospace !important;
        background-color: var(--secondary-bg) !important;
        color: var(--accent-yellow) !important;
        padding: 2px 6px !important;
    }
    pre {
        background-color: var(--secondary-bg) !important;
        border: 1px solid var(--border-color) !important;
        padding: 15px !important;
    }
    
    /* Dividers */
    hr {
        border-top: 1px solid var(--border-color) !important;
    }

    /* Custom classes for the WOW effect */
    .fcc-card {
        background-color: var(--secondary-bg);
        border: 1px solid var(--border-color);
        padding: 20px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Set Llama 4 models as constants
OUTLINE_MODEL = "llama-3.3-70b-versatile"
CONTENT_MODEL = "llama-3.3-70b-versatile"
      
class GenerationStatistics:
    def __init__(self, input_time=0,output_time=0,input_tokens=0,output_tokens=0,total_time=0,model_name="meta-llama/llama-4-scout-17b-16e-instruct"):
        self.input_time = input_time
        self.output_time = output_time
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_time = total_time # Sum of queue, prompt (input), and completion (output) times
        self.model_name = model_name

    def get_input_speed(self):
        """ 
        Tokens per second calculation for input
        """
        if self.input_time != 0:
            return self.input_tokens / self.input_time
        else:
            return 0
    
    def get_output_speed(self):
        """ 
        Tokens per second calculation for output
        """
        if self.output_time != 0:
            return self.output_tokens / self.output_time
        else:
            return 0
    
    def add(self, other):
        """
        Add statistics from another GenerationStatistics object to this one.
        """
        if not isinstance(other, GenerationStatistics):
            raise TypeError("Can only add GenerationStatistics objects")
        
        self.input_time += other.input_time
        self.output_time += other.output_time
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.total_time += other.total_time

    def __str__(self):
        return (f"\n## {self.get_output_speed():.2f} T/s ⚡\nRound trip time: {self.total_time:.2f}s  Model: {self.model_name}\n\n"
                f"| Metric          | Input          | Output          | Total          |\n"
                f"|-----------------|----------------|-----------------|----------------|\n"
                f"| Speed (T/s)     | {self.get_input_speed():.2f}            | {self.get_output_speed():.2f}            | {(self.input_tokens + self.output_tokens) / self.total_time if self.total_time != 0 else 0:.2f}            |\n"
                f"| Tokens          | {self.input_tokens}            | {self.output_tokens}            | {self.input_tokens + self.output_tokens}            |\n"
                f"| Inference Time (s) | {self.input_time:.2f}            | {self.output_time:.2f}            | {self.total_time:.2f}            |")

class NoteSection:
    def __init__(self, structure, transcript, speaker_info=None):
        self.structure = structure
        self.contents = {title: "" for title in self.flatten_structure(structure)}
        self.placeholders = {title: st.empty() for title in self.flatten_structure(structure)}
        self.speaker_info = speaker_info if speaker_info else {}

        # Display speaker information prominently
        if self.speaker_info and self.speaker_info.get("speaker_count", 0) > 0:
            self.display_speaker_info()
        
        st.markdown("## Raw transcript:")
        st.markdown(transcript)
        st.markdown("---")
    
    def display_speaker_info(self):
        """Display speaker identification information"""
        if not self.speaker_info:
            return
        
        st.markdown("---")
        st.markdown("### 👥 Speaker Information")
        
        # Speaker count
        speaker_count = self.speaker_info.get("speaker_count", 0)
        st.markdown(f"<p style='color: #000000; font-size: 1.1em;'><strong style='color: #0066cc;'>Number of Speakers:</strong> <span style='color: #000000;'>{speaker_count}</span></p>", unsafe_allow_html=True)
        
        # Individual speaker details
        speakers = self.speaker_info.get("speakers", [])
        if speakers:
            st.markdown("<p style='color: #000000; font-size: 1.1em; margin-top: 15px;'><strong style='color: #0066cc;'>Speakers Identified:</strong></p>", unsafe_allow_html=True)
            for idx, speaker in enumerate(speakers, 1):
                identifier = speaker.get("identifier", f"Speaker {idx}")
                role = speaker.get("role_or_title", "")
                brief_info = speaker.get("brief_info", "")
                
                speaker_card = f"""
                <div style='background-color: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #0066cc; border: 1px solid #cccccc;'>
                    <h4 style='color: #000000; margin-top: 0; font-weight: 600;'>👤 {identifier}</h4>
                """
                if role:
                    speaker_card += f"<p style='margin: 5px 0; color: #000000;'><strong style='color: #0066cc;'>Role/Title:</strong> {role}</p>"
                if brief_info:
                    speaker_card += f"<p style='margin: 5px 0; color: #000000;'><strong style='color: #0066cc;'>Information:</strong> {brief_info}</p>"
                speaker_card += "</div>"
                st.markdown(speaker_card, unsafe_allow_html=True)
        
        # Speaker mentions summary
        mentions = self.speaker_info.get("speaker_mentions", "")
        if mentions:
            st.info(f"ℹ️ {mentions}")
        
        st.markdown("---")

    def flatten_structure(self, structure):
        sections = []
        for title, content in structure.items():
            sections.append(title)
            if isinstance(content, dict):
                sections.extend(self.flatten_structure(content))
        return sections

    def update_content(self, title, new_content):
        try:
            self.contents[title] += new_content
            self.display_content(title)
        except TypeError as e:
            pass

    def display_content(self, title):
        try:
            if self.contents.get(title, "").strip():
                # Add visual enhancements with icons and styling
                icon = self._get_section_icon(title)
                styled_title = f"## {icon} {title}"
                # Add highlighted key points and better formatting
                styled_content = self._enhance_content(self.contents[title])
                self.placeholders[title].markdown(f"{styled_title}\n{styled_content}")
        except Exception as e:
            # Fallback to simple display if enhancement fails
            if self.contents.get(title, "").strip():
                self.placeholders[title].markdown(f"## {title}\n{self.contents[title]}")
    
    def _get_section_icon(self, title):
        """Return appropriate icon/emoji based on section title"""
        title_lower = title.lower()
        if any(word in title_lower for word in ['intro', 'overview', 'summary']):
            return "📋"
        elif any(word in title_lower for word in ['concept', 'theory', 'principle']):
            return "💡"
        elif any(word in title_lower for word in ['example', 'case', 'application']):
            return "📝"
        elif any(word in title_lower for word in ['conclusion', 'summary', 'wrap']):
            return "🎯"
        elif any(word in title_lower for word in ['method', 'approach', 'technique']):
            return "🔬"
        elif any(word in title_lower for word in ['result', 'finding', 'outcome']):
            return "📊"
        else:
            return "📌"
    
    def _enhance_content(self, content):
        """Enhance content with visual formatting"""
        # Add highlighting for key points (lines starting with bullet points or numbers)
        lines = content.split('\n')
        enhanced_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('-') or stripped.startswith('*') or (stripped and stripped[0].isdigit() and '.' in stripped[:3]):
                # Highlight key points
                enhanced_lines.append(f"**{line}**")
            elif stripped.startswith('**') or stripped.startswith('#'):
                # Already formatted
                enhanced_lines.append(line)
            else:
                enhanced_lines.append(line)
        return '\n'.join(enhanced_lines)

    def return_existing_contents(self, level=1) -> str:
        existing_content = ""
        for title, content in self.structure.items():
            if self.contents[title].strip():  # Only include title if there is content
                existing_content += f"{'#' * level} {title}\n{self.contents[title]}.\n\n"
            if isinstance(content, dict):
                existing_content += self.get_markdown_content(content, level + 1)
        return existing_content

    def display_structure(self, structure=None, level=1):
        if structure is None:
            structure = self.structure
        
        for title, content in structure.items():
            if self.contents.get(title, "").strip():  # Only display title if there is content
                try:
                    icon = self._get_section_icon(title)
                    # Add colored divider for visual separation using markdown (cream and black theme)
                    st.markdown(f"<div style='border-left: 4px solid #0066cc; padding: 15px; margin: 15px 0; margin-bottom: 20px; background-color: white; border-radius: 5px; border: 1px solid #cccccc;'>", unsafe_allow_html=True)
                    st.markdown(f"{'#' * level} {icon} {title}")
                    styled_content = self._enhance_content(self.contents[title])
                    self.placeholders[title].markdown(styled_content)
                    st.markdown("</div>", unsafe_allow_html=True)
                except Exception as e:
                    # Fallback to simple display
                    st.markdown(f"{'#' * level} {title}")
                    self.placeholders[title].markdown(self.contents[title])
            if isinstance(content, dict):
                self.display_structure(content, level + 1)

    def display_toc(self, structure, columns, level=1, col_index=0):
        for title, content in structure.items():
            with columns[col_index % len(columns)]:
                st.markdown(f"{' ' * (level-1) * 2}- {title}")
            col_index += 1
            if isinstance(content, dict):
                col_index = self.display_toc(content, columns, level + 1, col_index)
        return col_index

    def get_markdown_content(self, structure=None, level=1, include_speaker_info=True):
        """
        Returns the markdown styled pure string with the contents.
        """
        if structure is None:
            structure = self.structure
        
        markdown_content = ""
        
        # Add speaker information at the beginning if available (only once at top level)
        if include_speaker_info and level == 1 and self.speaker_info:
            markdown_content += "## 👥 Speaker Information\n\n"
            speaker_count = self.speaker_info.get("speaker_count", 0)
            markdown_content += f"**Number of Speakers:** {speaker_count}\n\n"
            
            speakers = self.speaker_info.get("speakers", [])
            if speakers:
                markdown_content += "**Speakers Identified:**\n\n"
                for idx, speaker in enumerate(speakers, 1):
                    identifier = speaker.get("identifier", f"Speaker {idx}")
                    role = speaker.get("role_or_title", "")
                    brief_info = speaker.get("brief_info", "")
                    
                    markdown_content += f"### 👤 {identifier}\n"
                    if role:
                        markdown_content += f"- **Role/Title:** {role}\n"
                    if brief_info:
                        markdown_content += f"- **Information:** {brief_info}\n"
                    markdown_content += "\n"
            
            mentions = self.speaker_info.get("speaker_mentions", "")
            if mentions:
                markdown_content += f"*Note: {mentions}*\n\n"
            markdown_content += "---\n\n"
        
        for title, content in structure.items():
            if self.contents[title].strip():  # Only include title if there is content
                markdown_content += f"{'#' * level} {title}\n{self.contents[title]}.\n\n"
            if isinstance(content, dict):
                markdown_content += self.get_markdown_content(content, level + 1, include_speaker_info=False)
        return markdown_content

def create_markdown_file(content: str) -> BytesIO:
    """
    Create a Markdown file from the provided content.
    """
    markdown_file = BytesIO()
    markdown_file.write(content.encode('utf-8'))
    markdown_file.seek(0)
    return markdown_file

def create_pdf_file(content: str, filename: str = "generated_notes", flowchart_data: dict = None):
    """
    Create a PDF file from the provided content with enhanced formatting.
    Uses md2pdf if available, otherwise falls back to fpdf2.
    """
    if not PDF_AVAILABLE:
        raise RuntimeError("PDF generation is not available on this system.")
    
    if MD2PDF_AVAILABLE:
        try:
            pdf_buffer = BytesIO()
            enhanced_content = _enhance_markdown_for_pdf(content)
            if flowchart_data and flowchart_data.get("topics"):
                enhanced_content += _format_flowchart_for_pdf(flowchart_data)
            md2pdf(pdf_buffer, md_content=enhanced_content)
            pdf_buffer.seek(0)
            return pdf_buffer
        except Exception as e:
            if FPDF_AVAILABLE:
                return _create_pdf_with_fpdf(content, filename, flowchart_data)
            else:
                raise RuntimeError(f"PDF generation failed: {str(e)}")
    
    if FPDF_AVAILABLE:
        return _create_pdf_with_fpdf(content, filename, flowchart_data)
    
    raise RuntimeError("PDF generation is not available on this system.")

def _format_flowchart_for_pdf(flowchart_data: dict) -> str:
    """Format flowchart data as a readable text section for PDF."""
    if not flowchart_data or not flowchart_data.get("topics"):
        return ""
    section = "\n\n---\n\n## Topic Flowchart\n\n"
    categories = {"start": [], "step": [], "decision": [], "end": []}
    for topic in flowchart_data["topics"]:
        cat = topic.get("category", "step")
        categories.get(cat, categories["step"]).append(topic.get("name", "Unknown"))
    if categories["start"]:
        section += "**Starting Points:** " + ", ".join(categories["start"]) + "\n\n"
    if categories["step"]:
        section += "**Core Topics:**\n"
        for t in categories["step"]:
            section += f"- {t}\n"
        section += "\n"
    if categories["decision"]:
        section += "**Key Decisions:** " + ", ".join(categories["decision"]) + "\n\n"
    if categories["end"]:
        section += "**Conclusions:** " + ", ".join(categories["end"]) + "\n\n"
    relationships = flowchart_data.get("relationships", [])
    if relationships:
        section += "**Topic Flow:**\n"
        for rel in relationships:
            fr, to = rel.get("from", "?"), rel.get("to", "?")
            label = rel.get("label", "")
            section += f"- {fr} --> {to}" + (f" ({label})" if label else "") + "\n"
    return section

def _enhance_markdown_for_pdf(content: str) -> str:
    """Enhance markdown content for better PDF rendering"""
    # Add header with EchoMind branding
    header = "# EchoMind Generated Notes\n\n---\n\n"
    # Ensure proper spacing
    enhanced = content.replace('\n\n\n', '\n\n')  # Remove excessive line breaks
    return header + enhanced

def _create_pdf_with_fpdf(content: str, filename: str = "generated_notes", flowchart_data: dict = None):
    """Create a visually engaging PDF with styled headers, colored sections, and box-diagram flowchart."""
    import re
    
    NAVY = (10, 10, 35)
    GREEN = (25, 135, 84)
    DARK_GRAY = (59, 59, 79)
    LIGHT_BG = (245, 246, 250)
    WHITE = (255, 255, 255)
    TEXT_DARK = (30, 30, 50)
    TEXT_MED = (80, 80, 100)
    BLUE = (0, 102, 204)
    ORANGE = (255, 165, 0)
    RED = (214, 39, 40)
    PURPLE = (148, 103, 189)
    
    def clean(text):
        if not text: return ""
        out = ""
        for c in text:
            code = ord(c)
            if 32 <= code <= 126 or c in '\n\r\t': out += c
            elif c in '\u2014\u2013': out += '-'
            elif c in '\u201c\u201d\u201e\u201f': out += '"'
            elif c in '\u2018\u2019\u201a\u201b': out += "'"
            elif c == '\u2026': out += '...'
        return out
    
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # ===== TITLE PAGE =====
    pdf.add_page()
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, 210, 100, 'F')
    pdf.set_fill_color(*GREEN)
    pdf.rect(0, 100, 210, 3, 'F')
    pdf.set_y(30)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Arial", "B", 30)
    pdf.cell(0, 14, "EchoMind", 0, 1, "C")
    pdf.set_font("Arial", size=13)
    pdf.cell(0, 8, "Intelligent Notes Generator", 0, 1, "C")
    pdf.ln(8)
    pdf.set_font("Arial", "I", 11)
    title_display = clean(filename.replace('_', ' ').replace('-', ' '))
    if len(title_display) > 60: title_display = title_display[:57] + "..."
    pdf.cell(0, 6, title_display, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(115)
    pdf.set_text_color(*TEXT_DARK)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, "MIT ADT University, Pune", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Arial", size=9)
    pdf.set_text_color(*TEXT_MED)
    pdf.cell(0, 5, "Pratik Dalvi | Sushant Marathe | Abhinav Anand | Sushmita Shinde", align="C", new_x="LMARGIN", new_y="NEXT")
    
    # ===== CONTENT =====
    pdf.add_page()
    content = clean(content)
    lines = content.split('\n')
    sec_colors = [GREEN, BLUE, PURPLE, RED, ORANGE]
    sec_count = 0
    
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            pdf.ln(3)
            i += 1
            continue
        
        if line.startswith('#'):
            hl = len(line) - len(line.lstrip('#'))
            ht = clean(line.lstrip('#').strip())
            if ht:
                color = sec_colors[sec_count % len(sec_colors)]
                if hl <= 2:
                    sec_count += 1
                    pdf.ln(6)
                    y = pdf.get_y()
                    pdf.set_fill_color(*color)
                    pdf.rect(10, y, 3, 10, 'F')
                    pdf.set_x(16)
                    pdf.set_text_color(*color)
                    pdf.set_font("Arial", "B", 15 if hl == 1 else 13)
                    pdf.cell(0, 10, ht, new_x="LMARGIN", new_y="NEXT")
                    pdf.set_draw_color(*color)
                    pdf.set_line_width(0.3)
                    pdf.line(16, pdf.get_y(), 190, pdf.get_y())
                    pdf.ln(3)
                else:
                    pdf.ln(4)
                    pdf.set_text_color(*DARK_GRAY)
                    pdf.set_font("Arial", "B", 11)
                    pdf.cell(0, 7, ht, new_x="LMARGIN", new_y="NEXT")
                    pdf.ln(2)
                pdf.set_text_color(*TEXT_DARK)
                pdf.set_font("Arial", size=10)
        elif re.match(r'^-{3,}$', line):
            pdf.ln(4)
            pdf.set_draw_color(*GREEN)
            pdf.set_line_width(0.4)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.set_line_width(0.2)
            pdf.ln(4)
        elif re.match(r'^\s*[-*+]\s+', line) or re.match(r'^\s*\d+\.\s+', line):
            lt = re.sub(r'^\s*[-*+]\s+', '', line)
            lt = re.sub(r'^\s*\d+\.\s+', '', lt)
            lt = re.sub(r'\*\*|__', '', lt)
            lt = clean(lt)
            if lt.strip():
                pdf.set_fill_color(*GREEN)
                pdf.rect(16, pdf.get_y() + 1.5, 2, 2, 'F')
                pdf.set_x(22)
                pdf.set_text_color(*TEXT_DARK)
                pdf.set_font("Arial", size=10)
                pdf.multi_cell(165, 5.5, lt.strip())
                pdf.ln(1)
        elif re.match(r'^\*\*.*\*\*$', line) or re.match(r'^__.*__$', line):
            bt = re.sub(r'\*\*|__', '', line).strip()
            bt = clean(bt)
            if bt:
                pdf.set_font("Arial", "B", 10)
                pdf.set_text_color(*DARK_GRAY)
                pdf.multi_cell(0, 5.5, bt)
                pdf.set_font("Arial", size=10)
                pdf.set_text_color(*TEXT_DARK)
                pdf.ln(1.5)
        else:
            cl = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)
            cl = re.sub(r'\*([^*]+)\*', r'\1', cl)
            cl = re.sub(r'__([^_]+)__', r'\1', cl)
            cl = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', cl)
            cl = re.sub(r'`([^`]+)`', r'\1', cl)
            cl = clean(cl)
            if cl.strip():
                pdf.set_text_color(*TEXT_DARK)
                pdf.set_font("Arial", size=10)
                pdf.multi_cell(0, 5.5, cl.strip())
                pdf.ln(1.5)
        i += 1
    
    # ===== FLOWCHART PAGE =====
    if flowchart_data and flowchart_data.get("topics"):
        pdf.add_page('L')
        # Header
        pdf.set_fill_color(*NAVY)
        pdf.rect(0, 0, 297, 22, 'F')
        pdf.set_fill_color(*GREEN)
        pdf.rect(0, 22, 297, 2, 'F')
        pdf.set_y(5)
        pdf.set_text_color(*WHITE)
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 12, "Topic Flowchart", align="C", new_x="LMARGIN", new_y="NEXT")
        
        topics = flowchart_data.get("topics", [])
        relationships = flowchart_data.get("relationships", [])
        cat_colors = {"start": GREEN, "step": BLUE, "decision": ORANGE, "end": RED}
        cat_fills = {"start": (230, 245, 235), "step": (230, 240, 255), "decision": (255, 240, 220), "end": (250, 230, 230)}
        
        # New Layout: Simple Vertical Sequence with centered boxes
        # This prevents crossing lines and makes the "structure" clear
        bw, bh = 85, 18
        center_x = 297 / 2
        start_y = 35
        # Dynamic gap adjustment based on topic count
        gap_y = max(10, min(25, 120 // len(topics))) if topics else 25
        
        positions = {}
        for idx, topic in enumerate(topics):
            x = center_x - bw/2
            y = start_y + idx * (bh + gap_y)
            cat = topic.get("category", "step")
            color = cat_colors.get(cat, BLUE)
            fill = cat_fills.get(cat, (230, 240, 255))
            name = clean(topic.get("name", "Unknown"))
            
            # Store connection points
            # Top-middle and Bottom-middle
            positions[name] = {
                "top": (center_x, y),
                "bottom": (center_x, y + bh),
                "left": (x, y + bh/2),
                "right": (x + bw, y + bh/2)
            }
            
            # Draw box
            pdf.set_fill_color(*fill)
            pdf.set_draw_color(*color)
            pdf.set_line_width(0.7)
            # Round corners or special shape for decision
            if cat == "decision":
                pdf.rect(x - 2, y, bw + 4, bh, 'FD') # Slightly wider for decision
            else:
                pdf.rect(x, y, bw, bh, 'FD')
            
            # Text scaling for box
            pdf.set_text_color(*color)
            font_size = 9 if len(name) < 30 else 7.5
            pdf.set_font("Arial", "B", font_size)
            pdf.set_xy(x + 2, y + 3)
            # Use multi_cell for wrapping or just cell for single line
            pdf.cell(bw - 4, 6, name[:45] + (".." if len(name) > 45 else ""), align="C", new_x="LMARGIN", new_y="NEXT")
            
            # Category label at bottom of box
            pdf.set_font("Arial", "I", 6)
            pdf.set_text_color(*TEXT_MED)
            pdf.set_xy(x + 2, y + bh - 7)
            pdf.cell(bw - 4, 4, f"({cat.upper()})", align="C", new_x="LMARGIN", new_y="NEXT")
        
        # Draw Connections with Arrowheads
        pdf.set_draw_color(*DARK_GRAY)
        pdf.set_line_width(0.6)
        for rel in relationships:
            fr_name, to_name = clean(rel.get("from", "")), clean(rel.get("to", ""))
            if fr_name in positions and to_name in positions:
                start = positions[fr_name]["bottom"]
                end = positions[to_name]["top"]
                
                # Check relative positions for routing
                idx_fr = topics.index(next(t for t in topics if clean(t.get("name","")) == fr_name))
                idx_to = topics.index(next(t for t in topics if clean(t.get("name","")) == to_name))
                
                if idx_to == idx_fr + 1:
                    # Direct consecutive: Straight line
                    pdf.line(start[0], start[1], end[0], end[1])
                else:
                    # Non-consecutive: Elbow connector to side
                    pdf.set_line_width(0.4)
                    mid_x = start[0] + (bw/2 + 5) if idx_to > idx_fr else start[0] - (bw/2 + 5)
                    pdf.line(start[0], start[1], start[0], start[1] + gap_y/2)
                    pdf.line(start[0], start[1] + gap_y/2, mid_x, start[1] + gap_y/2)
                    pdf.line(mid_x, start[1] + gap_y/2, mid_x, end[1] - gap_y/2)
                    pdf.line(mid_x, end[1] - gap_y/2, end[0], end[1] - gap_y/2)
                    pdf.line(end[0], end[1] - gap_y/2, end[0], end[1])
                    pdf.set_line_width(0.6)
                
                # Draw Arrowhead (triangle) at 'end'
                pdf.set_fill_color(*DARK_GRAY)
                # Triangle points: top-middle (end), bottom-left, bottom-right
                pdf.polygon([(end[0], end[1]), (end[0]-1.5, end[1]-3), (end[0]+1.5, end[1]-3)], style='F')
        
        # Legend at bottom right
        pdf.set_y(210 - 35)
        pdf.set_x(230)
        pdf.set_font("Arial", "B", 8)
        pdf.set_text_color(*TEXT_DARK)
        pdf.cell(0, 5, "Legend:", new_x="LMARGIN", new_y="NEXT")
        for cat, color in cat_colors.items():
            pdf.set_x(230)
            pdf.set_fill_color(*color)
            pdf.rect(pdf.get_x(), pdf.get_y()+1, 4, 3, 'F')
            pdf.set_x(236)
            pdf.cell(0, 5, cat.title(), new_x="LMARGIN", new_y="NEXT")
    
    # Footer
    pdf.ln(6)
    pdf.set_draw_color(*GREEN)
    pw = 190 if pdf.cur_orientation == 'P' else 277
    pdf.line(20, pdf.get_y(), pw, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(*TEXT_MED)
    pdf.cell(0, 5, "Generated by EchoMind | MIT ADT University, Pune | 2025", align="C", new_x="LMARGIN", new_y="NEXT")
    
    buf = BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf

def extract_topics_and_relationships(notes_content: str, model: str = "llama-3.3-70b-versatile"):
    """
    Extract topics and their relationships from notes content using LLM.
    Categorizes topics for professional flowchart representation.
    """
    try:
        # Limit content to avoid token limits
        limited_content = notes_content[:8000]
        prompt = f"""Analyze the following notes and extract a structured flowchart data.
Each topic must be categorized appropriately to create a logical process flow:
- Categorize as 'start' for the beginning of the process.
- Categorize as 'decision' for branching points or questions.
- Categorize as 'step' for standard actions or concepts.
- Categorize as 'end' for the final conclusion or result.

Notes Content:
{limited_content}

Provide your response in JSON format:
{{
    "topics": [
        {{
            "name": "Topic name",
            "description": "Brief description",
            "category": "start|step|decision|end"
        }}
    ],
    "relationships": [
        {{
            "from": "Source topic",
            "to": "Target topic",
            "type": "leads_to|depends_on|part_of|related_to",
            "label": "Yes/No or relationship label"
        }}
    ]
}}

Ensure the relationships create a clean, hierarchical flow from START to END."""

        completion = st.session_state.groq.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at analyzing content and extracting logical flows. Categorize topics accurately (start, step, decision, end) to ensure a professional flowchart structure."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=4000,
            top_p=1,
            stream=False,
            response_format={"type": "json_object"},
            stop=None,
        )

        result = json.loads(completion.choices[0].message.content)
        return result
    except Exception as e:
        st.error(f"Error extracting topics: {str(e)}")
        return {"topics": [], "relationships": []}

def generate_mermaid_flowchart(topics_data: dict):
    """
    Generate a clean, professional Mermaid flowchart string from topics and relationships.
    Uses the peach/orange and dark-navy theme from the user's reference.
    """
    topics = topics_data.get("topics", [])
    relationships = topics_data.get("relationships", [])
    if not topics:
        return None
    
    mermaid_lines = ["graph TD"]
    
    # Define styles to match the peach/orange theme
    mermaid_lines.append("    %% Styling")
    mermaid_lines.append("    classDef startEnd fill:#fecc4c,stroke:#3b3b4f,stroke-width:2px,color:#1b1b32;")
    mermaid_lines.append("    classDef step fill:#ffffff,stroke:#3b3b4f,stroke-width:2px,color:#1b1b32;")
    mermaid_lines.append("    classDef decision fill:#fecc4c,stroke:#3b3b4f,stroke-width:2px,color:#1b1b32;")
    mermaid_lines.append("    classDef default font-family:Lato,font-size:14px;")
    
    # Process topics
    topic_ids = {}
    for i, topic in enumerate(topics):
        t_id = f"node{i}"
        topic_ids[topic["name"]] = t_id
        name = topic["name"].replace('"', "'")
        category = topic.get("category", "step").lower()
        
        # Select shape based on category
        if category == "start" or category == "end":
            shape_start, shape_end = "([", "])" # Ellipse/Stadium
            style_class = "startEnd"
        elif category == "decision":
            shape_start, shape_end = "{", "}" # Diamond
            style_class = "decision"
        else:
            shape_start, shape_end = "[", "]" # Rectangle
            style_class = "step"
            
        mermaid_lines.append(f'    {t_id}{shape_start}"{name}"{shape_end}::: {style_class}')
    
    # Process relationships
    for rel in relationships:
        u_name = rel.get("from")
        v_name = rel.get("to")
        label = rel.get("label", "")
        
        if u_name in topic_ids and v_name in topic_ids:
            u_id = topic_ids[u_name]
            v_id = topic_ids[v_name]
            if label:
                mermaid_lines.append(f'    {u_id} -- "{label}" --> {v_id}')
            else:
                mermaid_lines.append(f'    {u_id} --> {v_id}')
                
    # Fallback if no relationships
    if not relationships and len(topics) > 1:
        for i in range(len(topics) - 1):
            mermaid_lines.append(f'    node{i} --> node{i+1}')
            
    return "\n".join(mermaid_lines)

def generate_flowchart(topics_data: dict, filename: str = "flowchart"):
    """Legacy wrapper that now returns Mermaid code as a string."""
    return generate_mermaid_flowchart(topics_data)

def generate_architecture_diagram(topics_data: dict, filename: str = "architecture_diagram"):
    """Generates an architecture diagram using Mermaid with a different layout."""
    mermaid_code = generate_mermaid_flowchart(topics_data)
    if mermaid_code:
        return mermaid_code.replace("graph TD", "graph LR") # Horizontal for architecture
    return None

def text_to_speech_azure(text: str):
    """Convert text to speech using Azure Cognitive Services"""
    if not AZURE_SPEECH_AVAILABLE or not AZURE_SPEECH_KEY or not AZURE_REGION:
        return None
    
    try:
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_REGION)
        # Use neural voice for better quality
        speech_config.speech_synthesis_voice_name = "en-US-AriaNeural"
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
        
        # Synthesize to audio stream
        result = synthesizer.speak_text_async(text).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return result.audio_data
        else:
            return None
    except Exception as e:
        st.error(f"TTS Error: {str(e)}")
        return None

def get_notes_text_for_tts():
    """Extract plain text from notes for TTS"""
    if "notes" not in st.session_state:
        return None
    
    notes = st.session_state.notes
    # Get all content as plain text (remove markdown formatting)
    full_text = notes.get_markdown_content()
    # Remove markdown headers and formatting for cleaner TTS
    import re
    # Remove markdown headers
    full_text = re.sub(r'^#+\s+', '', full_text, flags=re.MULTILINE)
    # Remove markdown bold/italic
    full_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', full_text)
    full_text = re.sub(r'\*([^*]+)\*', r'\1', full_text)
    return full_text

def transcribe_audio(audio_file, language="en"):
    """
    Transcribes audio using Groq's Whisper API with language support.
    """
    kwargs = {
        "file": audio_file,
        "model": "whisper-large-v3",
        "prompt": "",
        "response_format": "json",
        "temperature": 0.0,
    }
    # Only set language if not auto-detect
    if language and language != "auto":
        kwargs["language"] = language
    
    transcription = st.session_state.groq.audio.transcriptions.create(**kwargs)
    return transcription.text

def identify_speakers(transcript: str, model: str = "meta-llama/llama-4-scout-17b-16e-instruct"):
    """
    Identify speakers, count them, and extract brief information about them from the transcript.
    Returns a dictionary with speaker information.
    """
    try:
        prompt = f"""Analyze the following transcript and identify all speakers. For each speaker, determine:
1. How many distinct speakers are present
2. If speakers are named or identified, note their names/identifiers
3. Any brief information mentioned about each speaker (role, title, background, etc.)

Transcript:
{transcript[:5000]}

Provide your response in JSON format:
{{
    "speaker_count": <number>,
    "speakers": [
        {{
            "identifier": "<name or Speaker 1, Speaker 2, etc.>",
            "role_or_title": "<if mentioned>",
            "brief_info": "<any information mentioned about this speaker>"
        }}
    ],
    "speaker_mentions": "<brief summary of how speakers are identified or mentioned>"
}}

If no clear speaker identification is possible, estimate based on context, dialogue patterns, and content changes."""

        completion = st.session_state.groq.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at analyzing conversations and identifying speakers. Extract speaker information accurately from transcripts."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=2000,
            top_p=1,
            stream=False,
            response_format={"type": "json_object"},
            stop=None,
        )

        speaker_info = json.loads(completion.choices[0].message.content)
        return speaker_info
    except Exception as e:
        # Fallback: basic speaker estimation
        import re
        # Try to identify speakers by common patterns
        speaker_count = 1
        speakers = []
        
        # Look for common speaker indicators
        if any(word in transcript.lower() for word in ['speaker', 'panelist', 'moderator', 'host', 'guest']):
            speaker_count = 2
        
        # Look for question-answer patterns (indicates multiple speakers)
        if transcript.count('?') > 5:
            speaker_count = max(speaker_count, 2)
        
        return {
            "speaker_count": speaker_count,
            "speakers": [{"identifier": f"Speaker {i+1}", "role_or_title": "", "brief_info": ""} for i in range(speaker_count)],
            "speaker_mentions": "Speaker identification could not be determined automatically."
        }

def generate_notes_structure(transcript: str, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct", note_style: str = "detailed"):
    """
    Returns notes structure content as well as total tokens and total time for generation.
    note_style: 'exam_ready', 'detailed', or 'with_examples'
    """

    shot_example = """
"Introduction": "Introduction to the AMA session, including the topic of Groq scaling architecture and the panelists",
"Panelist Introductions": "Brief introductions from Igor, Andrew, and Omar, covering their backgrounds and roles at Groq",
"Groq Scaling Architecture Overview": "High-level overview of Groq's scaling architecture, covering hardware, software, and cloud components",
"Hardware Perspective": "Igor's overview of Groq's hardware approach, using an analogy of city traffic management to explain the traditional compute approach and Groq's innovative approach",
"Traditional Compute": "Description of traditional compute approach, including asynchronous nature, queues, and poor utilization of infrastructure",
"Groq's Approach": "Description of Groq's approach, including pre-orchestrated movement of data, low latency, high energy efficiency, and high utilization of resources",
"Hardware Implementation": "Igor's explanation of the hardware implementation, including a comparison of GPU and LPU architectures"
}"""

    style_instructions = {
        "exam_ready": "Create a CONCISE structure with fewer sections. Focus only on key concepts, definitions, and exam-relevant points. Keep section descriptions brief.",
        "detailed": "Create a comprehensive structure. Section titles and content descriptions must be comprehensive. Quality over quantity.",
        "with_examples": "Create a comprehensive structure with extra sections for real-world examples and analogies. Each major concept should have an example section."
    }
    style_instruction = style_instructions.get(note_style, style_instructions["detailed"])

    completion = st.session_state.groq.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Write in JSON format:\n\n{\"Title of section goes here\":\"Description of section goes here\",\"Title of section goes here\":\"Description of section goes here\",\"Title of section goes here\":\"Description of section goes here\"}"
            },
            {
                "role": "user",
                "content": f"### Transcript {transcript}\n\n### Example\n\n{shot_example}### Instructions\n\n{style_instruction}\n\nCreate a structure for notes on the above transcribed audio."
            }
        ],
        temperature=0.3,
        max_tokens=8000,
        top_p=1,
        stream=False,
        response_format={"type": "json_object"},
        stop=None,
    )

    usage = completion.usage
    statistics_to_return = GenerationStatistics(input_time=usage.prompt_time, output_time=usage.completion_time, input_tokens=usage.prompt_tokens, output_tokens=usage.completion_tokens, total_time=usage.total_time, model_name=model)

    return statistics_to_return, completion.choices[0].message.content

def generate_section(transcript: str, existing_notes: str, section: str, model: str = "meta-llama/llama-4-scout-17b-16e-instruct", note_style: str = "detailed"):
    style_prompts = {
        "exam_ready": "You are an expert exam prep writer. Generate CONCISE, bullet-point notes. Use short sentences, key terms in bold, and focus on definitions, formulas, and exam-relevant facts. No fluff.",
        "detailed": "You are an expert writer. Generate comprehensive note content for the section provided based factually on the transcript provided. Do *not* repeat any content from previous sections. Do *not* include the section title/header in your response - only generate the content.",
        "with_examples": "You are an expert educator. Generate comprehensive notes AND include real-world examples, analogies, or case studies for each concept. Make concepts easy to understand with practical illustrations. Do *not* repeat any content from previous sections."
    }
    system_prompt = style_prompts.get(note_style, style_prompts["detailed"])

    stream = st.session_state.groq.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": f"### Transcript\n\n{transcript}\n\n### Existing Notes\n\n{existing_notes}\n\n### Instructions\n\nGenerate note content (without the section title) for this section only based on the transcript: \n\n{section}"
            }
        ],
        temperature=0.3,
        max_tokens=8000,
        top_p=1,
        stream=True,
        stop=None,
    )

    for chunk in stream:
        tokens = chunk.choices[0].delta.content
        if tokens:
            yield tokens
        if x_groq := chunk.x_groq:
            if not x_groq.usage:
                continue
            usage = x_groq.usage
            statistics_to_return = GenerationStatistics(input_time=usage.prompt_time, output_time=usage.completion_time, input_tokens=usage.prompt_tokens, output_tokens=usage.completion_tokens, total_time=usage.total_time, model_name=model)
            yield statistics_to_return

def generate_title(transcript: str, model: str = "llama-3.3-70b-versatile"):
    """Generate a concise topic title from the transcript using the LLM."""
    try:
        completion = st.session_state.groq.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a title generator. Given a transcript, output ONLY a short, descriptive title (5-10 words max) that captures the main topic. No quotes, no explanation, just the title."
                },
                {
                    "role": "user",
                    "content": f"Generate a title for this transcript:\n\n{transcript[:3000]}"
                }
            ],
            temperature=0.3,
            max_tokens=30,
            top_p=1,
            stream=False,
            stop=None,
        )
        title = completion.choices[0].message.content.strip().strip('"').strip("'")
        return title if title else "Untitled Notes"
    except Exception:
        return "Untitled Notes"


# Initialize session state variables
if 'button_disabled' not in st.session_state:
    st.session_state.button_disabled = False

if 'button_text' not in st.session_state:
    st.session_state.button_text = "Generate Notes"

if 'statistics_text' not in st.session_state:
    st.session_state.statistics_text = ""

if 'uploaded_filename' not in st.session_state:
    st.session_state.uploaded_filename = None

if 'live_audio_bytes' not in st.session_state:
    st.session_state.live_audio_bytes = None

if 'recording' not in st.session_state:
    st.session_state.recording = False

st.write("# 🧠 EchoMind")

def disable():
    st.session_state.button_disabled = True

def enable():
    st.session_state.button_disabled = False

def empty_st():
    st.empty()

# Database functions for storing and retrieving notes
def get_db_path():
    """Get database path with proper directory handling"""
    db_path = os.environ.get('DATABASE_PATH', 'echomind_notes.db')
    # Ensure directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir and db_dir.strip():  # Only create directory if path is not empty
        if not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
            except Exception as e:
                print(f"Warning: Could not create database directory {db_dir}: {e}")
                # Fallback to current directory
                db_path = os.path.basename(db_path)
    return db_path

def init_database():
    """Initialize the SQLite database for storing notes"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                filename TEXT,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        print(f"Database initialized successfully at: {db_path}")
    except Exception as e:
        print(f"Error initializing database: {e}")
        # Try fallback to current directory
        try:
            db_path = 'echomind_notes.db'
            conn = sqlite3.connect(db_path, check_same_thread=False)
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    filename TEXT,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            conn.close()
            print(f"Database initialized with fallback path: {db_path}")
        except Exception as e2:
            print(f"Critical: Could not initialize database: {e2}")

def save_note_to_db(title, filename, content):
    """Save a note to the database"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute('''
            INSERT INTO notes (title, filename, content, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, filename, content, datetime.now(), datetime.now()))
        conn.commit()
        note_id = c.lastrowid
        conn.close()
        return note_id
    except Exception as e:
        print(f"Error saving note to database: {e}")
        st.error(f"Could not save note to database: {str(e)}")
        return None

def get_all_notes():
    """Retrieve all notes from the database, ordered by most recent"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute('''
            SELECT id, title, filename, created_at, updated_at
            FROM notes
            ORDER BY updated_at DESC
        ''')
        notes = c.fetchall()
        conn.close()
        return notes
    except Exception as e:
        print(f"Error retrieving notes from database: {e}")
        return []

def get_note_by_id(note_id):
    """Retrieve a specific note by ID"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute('''
            SELECT id, title, filename, content, created_at, updated_at
            FROM notes
            WHERE id = ?
        ''', (note_id,))
        note = c.fetchone()
        conn.close()
        return note
    except Exception as e:
        print(f"Error retrieving note {note_id} from database: {e}")
        return None

def delete_note_from_db(note_id):
    """Delete a note from the database"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute('DELETE FROM notes WHERE id = ?', (note_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting note {note_id} from database: {e}")
        return False

# Initialize database on startup
try:
    init_database()
except Exception as e:
    print(f"Warning: Database initialization failed: {e}")
    print("Application will continue, but note saving may not work.")

try:
    with st.sidebar:
        st.write(f"# 🧠 EchoMind")
        st.markdown("Intelligent note generation powered by AI")
        
        st.write(f"---")
        
        # Notes History Section - above project information
        st.markdown("### 📚 Your Notes")
        
        # Get all saved notes
        saved_notes = get_all_notes()
        
        if saved_notes:
            st.markdown(f"<p style='color: #000000; font-size: 0.9em; margin-bottom: 10px;'>You have <strong style='color: #0066cc;'>{len(saved_notes)}</strong> saved note(s)</p>", unsafe_allow_html=True)
            
            # Display notes in an expandable container
            with st.expander("View All Notes", expanded=False):
                for note in saved_notes:
                    note_id, title, filename, created_at, updated_at = note
                    
                    # Format dates
                    try:
                        if isinstance(created_at, str):
                            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        else:
                            created_date = created_at
                        formatted_date = created_date.strftime("%Y-%m-%d %H:%M")
                    except:
                        formatted_date = str(created_at)[:16] if created_at else "Unknown"
                    
                    # Create a card for each note
                    st.markdown(f"""
                    <div style='padding: 12px; margin: 8px 0; background-color: white; border-radius: 6px; border: 1px solid #cccccc; border-left: 4px solid #0066cc;'>
                        <p style='color: #000000; margin: 0; font-weight: 600;'>{title}</p>
                        <p style='color: #666666; margin: 5px 0 0 0; font-size: 0.85em;'>
                            📄 {filename if filename else 'Untitled'}<br>
                            📅 {formatted_date}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Buttons for each note
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📖 View", key=f"view_{note_id}", use_container_width=True):
                            st.session_state.selected_note_id = note_id
                            st.rerun()
                    with col2:
                        if st.button("🗑️ Delete", key=f"delete_{note_id}", use_container_width=True):
                            if delete_note_from_db(note_id):
                                st.success("Note deleted!")
                                st.rerun()
                            else:
                                st.error("Failed to delete note. Please try again.")
                    
                    st.markdown("---")
        else:
            st.info("📝 No saved notes yet. Generate notes to see them here!")
        
        st.write(f"---")
        
        st.markdown("### 👥 Project Information")
        st.markdown("""
        <div style='padding: 15px; background-color: white; border-radius: 8px; border: 1px solid #cccccc;'>
            <p style='color: #000000; margin: 5px 0;'><strong style='color: #0066cc;'>Created by:</strong><br>Pratik Dalvi, Sushant Marathe,<br>Abhinav Anand, Sushmita Shinde</p>
            <p style='color: #000000; margin: 5px 0;'><strong style='color: #0066cc;'>Mentor:</strong><br> prof Dr. Manisha Galphade</p>
            <p style='color: #000000; margin: 5px 0;'><strong style='color: #0066cc;'>Major Project Group:</strong><br>LYCORE610</p>
            <p style='color: #000000; margin: 5px 0;'><strong style='color: #0066cc;'>Institution:</strong><br>School of Computing , MIT ADT University, Pune</p>
        </div>
        """, unsafe_allow_html=True)
    

    # Handle viewing selected note from sidebar
    if 'selected_note_id' in st.session_state and st.session_state.selected_note_id:
        note_data = get_note_by_id(st.session_state.selected_note_id)
        if note_data:
            note_id, title, filename, content, created_at, updated_at = note_data
            st.markdown("---")
            st.markdown(f"### 📖 Viewing: {title}")
            st.markdown(f"**File:** {filename if filename else 'Untitled'} | **Created:** {str(created_at)[:16] if created_at else 'Unknown'}")
            st.markdown("---")
            st.markdown(content)
            
            # Download buttons for viewed note
            col1, col2 = st.columns(2)
            with col1:
                markdown_file = create_markdown_file(content)
                st.download_button(
                    label='📄 Download as Text (.txt)',
                    data=markdown_file,
                    file_name=f'{title}_notes.txt',
                    mime='text/plain',
                    use_container_width=True,
                    key='download_txt_viewed'
                )
            with col2:
                if PDF_AVAILABLE:
                    try:
                        pdf_file = create_pdf_file(content, title)
                        st.download_button(
                            label='📑 Download as PDF (.pdf)',
                            data=pdf_file,
                            file_name=f'{title}_notes.pdf',
                            mime='application/pdf',
                            use_container_width=True,
                            key='download_pdf_viewed'
                        )
                    except Exception as e:
                        st.error(f"PDF generation failed: {str(e)}")
            
            if st.button("← Back to Current Notes"):
                del st.session_state.selected_note_id
                st.rerun()
            st.markdown("---")
    
    # --- Clean Input Section ---
    st.markdown("---")
    
    # Language selection (compact, inline)
    lang_col1, lang_col2 = st.columns([3, 1])
    with lang_col1:
        st.markdown("### 🎯 Create New Notes")
    with lang_col2:
        selected_lang = st.selectbox(
            "Language",
            options=list(SUPPORTED_LANGUAGES.keys()),
            index=0,
            key="lang_select",
            label_visibility="collapsed"
        )
    lang_code = SUPPORTED_LANGUAGES[selected_lang]
    
    # Four clean tabs for input
    tab_record, tab_upload, tab_youtube, tab_ppt = st.tabs(["🎤 Record", "📁 Upload File", "🔗 YouTube Link", "📊 PPT Analysis"])
    
    audio_file = None
    youtube_link = None
    input_method = "Upload audio file"
    
    with tab_record:
        try:
            if hasattr(st, 'audio_input'):
                recorded_audio = st.audio_input("Click the mic to start recording", key="live_recording")
                if recorded_audio:
                    st.session_state.uploaded_filename = "live_recording.wav"
                    st.session_state.live_audio_bytes = recorded_audio
                    st.success("✅ Recording captured! Click **Generate Notes** below.")
            else:
                st.info("Live recording requires Streamlit 1.33+. Please upload an audio file instead.")
        except Exception as e:
            st.info("Live recording is not available in this environment. Please upload an audio file instead.")
    
    with tab_upload:
        audio_file = st.file_uploader("Drop an audio file here", type=["mp3", "wav", "m4a", "webm", "mp4", "ogg"], label_visibility="collapsed")
        if audio_file:
            st.session_state.uploaded_filename = audio_file.name
            if hasattr(audio_file, 'read'):
                audio_file.seek(0)
                audio_bytes_data = audio_file.read()
                audio_file = BytesIO(audio_bytes_data)
                audio_file.name = st.session_state.uploaded_filename
    
    with tab_youtube:
        youtube_link = st.text_input("Paste a YouTube URL", placeholder="https://youtube.com/watch?v=...", label_visibility="collapsed")
    
    with tab_ppt:
        st.markdown("Upload a PowerPoint or PDF to analyze topics and get a curated YouTube playlist.")
        ppt_file = st.file_uploader("Upload .pptx or .pdf", type=["pptx", "pdf"], key="ppt_upload", label_visibility="collapsed")
        if ppt_file:
            if st.button("🔍 Analyze Document", type="primary", use_container_width=True):
                with st.spinner("📊 Extracting content and analyzing topics..."):
                    try:
                        from ppt_analyzer import extract_ppt_text, extract_pdf_text, analyze_ppt_topics, generate_playlist, render_ppt_analysis
                        
                        file_ext = ppt_file.name.rsplit('.', 1)[-1].lower() if ppt_file.name else ""
                        if file_ext == "pdf":
                            slides_data = extract_pdf_text(ppt_file)
                        else:
                            slides_data = extract_ppt_text(ppt_file)
                        
                        if not slides_data:
                            st.warning("No readable text found in the document.")
                        else:
                            st.info(f"📄 Extracted text from {len(slides_data)} pages/slides")
                            
                            analysis = analyze_ppt_topics(slides_data, st.session_state.groq)
                            st.session_state.ppt_analysis = analysis
                            
                            with st.spinner("🎬 Generating YouTube playlist recommendations..."):
                                playlist_data = generate_playlist(analysis, st.session_state.groq)
                                st.session_state.ppt_playlist = playlist_data
                    except ImportError as ie:
                        st.error(f"Missing dependency: {str(ie)}")
                    except Exception as e:
                        st.error(f"Analysis failed: {str(e)}")
        
        # Display results if available
        if st.session_state.get('ppt_analysis'):
            from ppt_analyzer import render_ppt_analysis
            render_ppt_analysis(
                st.session_state.ppt_analysis,
                st.session_state.get('ppt_playlist', {"playlist": []})
            )

    # Check if API key is set
    if not GROQ_API_KEY:
        st.error("⚠️ GROQ_API_KEY not found. Please set it in your `.env` file.")
        st.stop()
    
    # Note style selector
    st.markdown("#### 📏 Note Style")
    note_style_label = st.radio(
        "Choose note style",
        ["📝 Exam Ready", "📖 Detailed", "💡 With Examples"],
        index=1,
        horizontal=True,
        label_visibility="collapsed"
    )
    note_style_map = {"📝 Exam Ready": "exam_ready", "📖 Detailed": "detailed", "💡 With Examples": "with_examples"}
    note_style = note_style_map[note_style_label]
    
    # Generate Notes button
    generate_col1, generate_col2, generate_col3 = st.columns([1, 2, 1])
    with generate_col2:
        submitted = st.button(
            "🚀 Generate Notes",
            disabled=st.session_state.button_disabled,
            use_container_width=True,
            type="primary"
        )

    # Processing status containers
    status_text = st.empty()
    def display_status(text):
        status_text.write(text)
    def clear_status():
        status_text.empty()
    download_status_text = st.empty()
    def display_download_status(text: str):
        download_status_text.write(text)
    def clear_download_status():
        download_status_text.empty()
    placeholder = st.empty()
    def display_statistics():
        with placeholder.container():
            if st.session_state.statistics_text:
                if "Transcribing audio in background" not in st.session_state.statistics_text:
                    st.markdown(st.session_state.statistics_text + "\n\n---\n")
                else:
                    st.markdown(st.session_state.statistics_text)
            else:
                placeholder.empty()

    if submitted:
        disable()
        # Check for live recording first
        if st.session_state.get('live_audio_bytes'):
            live_audio = st.session_state.live_audio_bytes
            if hasattr(live_audio, 'read'):
                live_audio.seek(0)
                audio_bytes_data = live_audio.read()
            else:
                audio_bytes_data = live_audio
            audio_file = BytesIO(audio_bytes_data)
            audio_file.name = st.session_state.get('uploaded_filename', "live_recording.wav")
            st.session_state.uploaded_filename = audio_file.name
            input_method = "Upload audio file"
            st.session_state.live_audio_bytes = None
        
        # Determine input method from what's available
        if audio_file is not None:
            input_method = "Upload audio file"
        elif youtube_link:
            input_method = "YouTube link"
        
        if input_method == "Upload audio file" and audio_file is None:
            st.error("Please record audio, upload a file, or paste a YouTube link.")
            enable()
        elif input_method == "YouTube link" and not youtube_link:
            st.error("Please enter a YouTube link.")
            enable()
        else:
            st.session_state.button_disabled = True

        audio_file_path = None

        if input_method == "YouTube link":
            display_status("Downloading audio from YouTube link ....")
            audio_file_path = download_video_audio(youtube_link, display_download_status)
            if audio_file_path is None:
                st.error("Failed to download audio from YouTube link. Please try again.")
                enable()
                clear_status()
            else:
                display_status("Processing YouTube audio ....")
                with open(audio_file_path, 'rb') as f:
                    file_contents = f.read()
                audio_file = BytesIO(file_contents)
                if os.path.getsize(audio_file_path) > MAX_FILE_SIZE:
                    raise ValueError(FILE_TOO_LARGE_MESSAGE)
                audio_file.name = os.path.basename(audio_file_path)
                delete_download(audio_file_path)
            clear_download_status()

        display_status("Transcribing audio ....")
        transcription_text = transcribe_audio(audio_file, language=lang_code)
        st.session_state.transcription_text = transcription_text
        display_statistics()
        
        display_status("Detecting topic ....")
        smart_title = generate_title(transcription_text, model=CONTENT_MODEL)
        st.session_state.notes_title = smart_title
        st.session_state.uploaded_filename = smart_title
        
        display_status("Identifying speakers ....")
        speaker_info = identify_speakers(transcription_text, model=CONTENT_MODEL)
        st.session_state.speaker_info = speaker_info

        display_status("Generating notes structure ....")
        large_model_generation_statistics, notes_structure = generate_notes_structure(transcription_text, model=OUTLINE_MODEL, note_style=note_style)

        display_status("Generating notes ...")
        total_generation_statistics = GenerationStatistics(model_name=CONTENT_MODEL)
        clear_status()

        try:
            notes_structure_json = json.loads(notes_structure)
            notes = NoteSection(structure=notes_structure_json, transcript=transcription_text, speaker_info=speaker_info)
            
            if 'notes' not in st.session_state:
                st.session_state.notes = notes

            st.session_state.notes.display_structure()

            def stream_section_content(sections):
                for title, content in sections.items():
                    if isinstance(content, str):
                        content_stream = generate_section(transcript=transcription_text, existing_notes=notes.return_existing_contents(), section=(title + ": " + content), model=CONTENT_MODEL, note_style=note_style)
                        for chunk in content_stream:
                            chunk_data = chunk
                            if type(chunk_data) == GenerationStatistics:
                                total_generation_statistics.add(chunk_data)
                                st.session_state.statistics_text = str(total_generation_statistics)
                                display_statistics()
                            elif chunk is not None:
                                st.session_state.notes.update_content(title, chunk)
                    elif isinstance(content, dict):
                        stream_section_content(content)

            stream_section_content(notes_structure_json)
        except json.JSONDecodeError:
            st.error("Failed to decode the notes structure. Please try again.")

        enable()
        
        # Save notes to database with smart title
        if 'notes' in st.session_state:
            try:
                notes_content = st.session_state.notes.get_markdown_content()
                title = st.session_state.get('notes_title', 'Untitled Notes')
                filename = st.session_state.get('uploaded_filename', title)
                title = title.replace('_', ' ').replace('-', ' ').title()
                note_id = save_note_to_db(title, filename, notes_content)
                if note_id:
                    st.success(f"✅ Notes saved! (ID: {note_id})")
            except Exception as e:
                st.warning(f"Could not save notes: {str(e)}")
        
        # Clear flowchart state for new generation
        for key in ['flowchart_data', 'flowchart_code', 'flowchart_generated', 'architecture_code', 'architecture_diagram_generated']:
            if key in st.session_state:
                del st.session_state[key]


except Exception as e:
    st.session_state.button_disabled = False

    if hasattr(e, 'status_code') and e.status_code == 413:
        st.error(FILE_TOO_LARGE_MESSAGE)
    else:
        st.error(e)

    if st.button("Clear"):
        st.rerun()

# Flowchart section - generate and display flowchart
if "notes" in st.session_state:
    st.markdown("---")
    st.markdown("### 📊 Topic Flowchart")
    
    if FLOWCHART_AVAILABLE:
        # Check if flowchart has already been generated
        if 'flowchart_data' not in st.session_state:
            with st.spinner("🔄 Analyzing topics and generating flowchart..."):
                try:
                    notes_content = st.session_state.notes.get_markdown_content()
                    topics_data = extract_topics_and_relationships(notes_content, model=CONTENT_MODEL)
                    st.session_state.flowchart_data = topics_data
                    st.session_state.flowchart_generated = False
                except Exception as e:
                    st.error(f"Error extracting topics: {str(e)}")
                    st.session_state.flowchart_data = None
        
        # Generate flowchart if we have topics data
        flowchart_data = st.session_state.get('flowchart_data')
        if flowchart_data and flowchart_data.get("topics"):
            if 'flowchart_code' not in st.session_state or not st.session_state.get('flowchart_generated', False):
                with st.spinner("🎨 Generating flowchart visualization..."):
                    try:
                        mermaid_code = generate_mermaid_flowchart(flowchart_data)
                        st.session_state.flowchart_code = mermaid_code
                        st.session_state.flowchart_generated = True
                    except Exception as e:
                        st.error(f"Error generating flowchart: {str(e)}")
                        st.session_state.flowchart_code = None
            
            # Display flowchart
            flowchart_code = st.session_state.get('flowchart_code')
            if flowchart_code:
                st.markdown(f"```mermaid\n{flowchart_code}\n```")
                
                # Download flowchart button (as text file)
                base_filename = st.session_state.get('uploaded_filename') or 'generated_notes'
                if isinstance(base_filename, str) and base_filename.endswith(('.mp3', '.wav', '.m4a', '.webm')):
                    base_filename = os.path.splitext(base_filename)[0]
                base_filename = "".join(c for c in base_filename if c.isalnum() or c in (' ', '-', '_')).strip()
                if not base_filename:
                    base_filename = 'generated_notes'
                
                st.download_button(
                    label='📥 Download Flowchart (Mermaid Source)',
                    data=flowchart_code,
                    file_name=f'{base_filename}_flowchart.mmd',
                    mime='text/plain',
                    key='download_flowchart'
                )
                
                # Display topics and relationships info
                with st.expander("📋 View Topics and Relationships Details"):
                    topics_data = flowchart_data
                    st.markdown("#### Topics:")
                    for i, topic in enumerate(topics_data.get("topics", []), 1):
                        st.markdown(f"{i}. **{topic['name']}**: {topic.get('description', 'No description')}")
                    
                    if topics_data.get("relationships"):
                        st.markdown("#### Relationships:")
                        for rel in topics_data.get("relationships", []):
                            rel_type = rel.get("type", "related_to").replace("_", " ").title()
                            st.markdown(f"- **{rel['from']}** → **{rel['to']}** ({rel_type})")
            else:
                st.info("Flowchart generation in progress...")
        else:
            if flowchart_data is None:
                st.info("📊 Flowchart data not available. Please wait for topic extraction to complete.")
            else:
                st.info("📊 No topics found to generate flowchart. Make sure your notes contain clear topics and concepts.")
    else:
        st.info("📊 Flowchart generation is powered by Mermaid (built into Streamlit).")

# Architecture Diagram section - generate and display architecture diagram
if "notes" in st.session_state:
    st.markdown("---")
    st.markdown("### 🏗️ Architecture Diagram")
    
    if FLOWCHART_AVAILABLE:
        # Generate architecture diagram if we have topics data
        flowchart_data = st.session_state.get('flowchart_data')
        if flowchart_data and flowchart_data.get("topics"):
            if 'architecture_code' not in st.session_state or not st.session_state.get('architecture_diagram_generated', False):
                with st.spinner("🎨 Generating architecture diagram visualization..."):
                    try:
                        arch_code = generate_architecture_diagram(flowchart_data)
                        st.session_state.architecture_code = arch_code
                        st.session_state.architecture_diagram_generated = True
                    except Exception as e:
                        st.error(f"Error generating architecture diagram: {str(e)}")
                        st.session_state.architecture_code = None
            
            # Display architecture diagram
            architecture_code = st.session_state.get('architecture_code')
            if architecture_code:
                st.markdown(f"```mermaid\n{architecture_code}\n```")
                
                # Download architecture diagram button
                base_filename = st.session_state.get('uploaded_filename') or 'generated_notes'
                if isinstance(base_filename, str) and base_filename.endswith(('.mp3', '.wav', '.m4a', '.webm')):
                    base_filename = os.path.splitext(base_filename)[0]
                base_filename = "".join(c for c in base_filename if c.isalnum() or c in (' ', '-', '_')).strip()
                if not base_filename:
                    base_filename = 'generated_notes'
                
                st.download_button(
                    label='📥 Download Architecture Diagram (Mermaid Source)',
                    data=architecture_code,
                    file_name=f'{base_filename}_architecture_diagram.mmd',
                    mime='text/plain',
                    key='download_architecture_diagram'
                )
        else:
            if flowchart_data is None:
                st.info("🏗️ Architecture diagram data not available. Please wait for topic extraction to complete.")
            else:
                st.info("🏗️ No topics found to generate architecture diagram. Make sure your notes contain clear topics and concepts.")
    else:
        st.info("🏗️ Architecture diagram generation is powered by Mermaid (built into Streamlit).")

# Download section - outside form (Streamlit requirement: download buttons can't be in forms)
if "notes" in st.session_state:
    st.markdown("---")
    st.markdown("### 📥 Download Your Notes")
    
    # Get filename from uploaded file or use default
    base_filename = st.session_state.get('uploaded_filename') or 'generated_notes'
    if isinstance(base_filename, str) and base_filename.endswith(('.mp3', '.wav', '.m4a', '.webm')):
        base_filename = os.path.splitext(base_filename)[0]
    
    # Remove any invalid filename characters
    base_filename = "".join(c for c in base_filename if c.isalnum() or c in (' ', '-', '_')).strip()
    if not base_filename:
        base_filename = 'generated_notes'

    # Create two columns for download buttons
    download_col1, download_col2 = st.columns(2)
    
    with download_col1:
        # Always show text download option
        markdown_file = create_markdown_file(st.session_state.notes.get_markdown_content())
        st.download_button(
            label='📄 Download as Text (.txt)',
            data=markdown_file,
            file_name=f'{base_filename}_notes.txt',
            mime='text/plain',
            use_container_width=True,
            key='download_txt_main'
        )
    
    with download_col2:
        # Show PDF download option
        if PDF_AVAILABLE:
            try:
                pdf_file = create_pdf_file(st.session_state.notes.get_markdown_content(), base_filename, flowchart_data=st.session_state.get('flowchart_data'))
                st.download_button(
                    label='📑 Download as PDF (.pdf)',
                    data=pdf_file,
                    file_name=f'{base_filename}_notes.pdf',
                    mime='application/pdf',
                    use_container_width=True,
                    key='download_pdf_main'
                )
            except Exception as e:
                st.error(f"PDF generation failed: {str(e)}")
                st.info("💡 Please use the text download option instead.")
        else:
            st.info("📑 PDF download is not available. Please use the text download option.")


# Analytics and Learning Tools
if "notes" in st.session_state:
    st.markdown("---")
    st.markdown("### 🧠 Analytics & Learning Tools")
    
    # Create tabs for different analytical features
    tab_sentiment, tab_quiz, tab_flashcards, tab_listen = st.tabs(["📊 Sentiment", "📝 Quiz", "🗂️ Flashcards", "🔊 Listen"])
    
    with tab_sentiment:
        if 'sentiment_result' not in st.session_state:
            with st.spinner("Analyzing text sentiment and tone..."):
                from sentiment_analysis import analyze_sentiment_with_groq, render_sentiment_display
                notes_content = st.session_state.notes.get_markdown_content()
                st.session_state.sentiment_result = analyze_sentiment_with_groq(notes_content, st.session_state.groq)
        
        from sentiment_analysis import render_sentiment_display
        render_sentiment_display(st.session_state.sentiment_result)
        
    with tab_quiz:
        if 'quiz_data' not in st.session_state:
            with st.spinner("Generating an interactive quiz..."):
                from quiz_generator import generate_quiz
                notes_content = st.session_state.notes.get_markdown_content()
                st.session_state.quiz_data = generate_quiz(notes_content, st.session_state.groq)
        
        from quiz_generator import render_quiz
        render_quiz(st.session_state.quiz_data)
        
    with tab_flashcards:
        if 'flashcards' not in st.session_state:
            with st.spinner("Creating study flashcards..."):
                from flashcard_generator import generate_flashcards
                notes_content = st.session_state.notes.get_markdown_content()
                st.session_state.flashcards = generate_flashcards(notes_content, st.session_state.groq)
        
        from flashcard_generator import render_flashcards
        render_flashcards(st.session_state.flashcards)
    
    with tab_listen:
        notes_text = get_notes_text_for_tts()
        if notes_text:
            clean_text = notes_text[:8000]
            clean_text = clean_text.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$').replace('\n', '\\n').replace('\r', '\\r')
            tts_html = f"""
<div style="display: flex; gap: 12px; padding: 15px 0;">
<button onclick="speakNotes()" style="padding: 12px 24px; background: #198754; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 15px; font-weight: 600;">🎧 Play Notes</button>
<button onclick="stopSpeaking()" style="padding: 12px 24px; background: #d32f2f; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 15px; font-weight: 600;">⏹️ Stop</button>
</div>
<script>
const notesText = `{clean_text}`;
function speakNotes() {{
    if ('speechSynthesis' in window) {{
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(notesText);
        utterance.rate = 0.9; utterance.pitch = 1.0; utterance.volume = 1.0; utterance.lang = 'en-US';
        window.speechSynthesis.speak(utterance);
    }} else {{ alert('Text-to-speech not supported in your browser.'); }}
}}
function stopSpeaking() {{ if ('speechSynthesis' in window) window.speechSynthesis.cancel(); }}
</script>
"""
            st.markdown(tts_html, unsafe_allow_html=True)
        else:
            st.info("No notes available to read aloud.")

# Email section
if "notes" in st.session_state:
    st.markdown("---")
    st.markdown("### 📧 Email Your Notes")
    
    from email_service import EmailService
    email_service = EmailService()
    
    if not email_service.is_configured:
        st.warning("⚠️ Email service is not fully configured in .env. Please set SMTP_EMAIL and SMTP_PASSWORD.")
    else:
        with st.form("email_notes_form"):
            recipient = st.text_input("Recipient Email:", value=st.session_state.get('user_email', ''), placeholder="Enter email address")
            include_pdf = st.checkbox("Include PDF attachment", value=True)
            
            send_submitted = st.form_submit_button("🚀 Send Notes to Email")
            
            if send_submitted:
                if not recipient:
                    st.error("Please provide a recipient email.")
                else:
                    with st.spinner("Sending email..."):
                        notes_md = st.session_state.notes.get_markdown_content()
                        subject = f"EchoMind Notes: {st.session_state.uploaded_filename}"
                        
                        pdf_bytes = None
                        if include_pdf:
                            try:
                                pdf_bytes = create_pdf_file(notes_md, st.session_state.uploaded_filename)
                            except Exception as e:
                                st.warning(f"Could not generate PDF: {str(e)}")
                        
                        success, message = email_service.send_notes_email(
                            recipient_email=recipient,
                            subject=subject,
                            notes_content=notes_md,
                            attachment_bytes=pdf_bytes,
                            attachment_filename=f"{st.session_state.uploaded_filename}_notes.pdf" if pdf_bytes else None
                        )
                        
                        if success:
                            st.success(message)
                        else:
                            st.error(message)

# Footer with creator information

st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 20px; background-color: white; border-radius: 10px; margin-top: 30px; border: 1px solid #cccccc;'>
    <h3 style='color: #0066cc; margin-top: 0;'>🧠 EchoMind © 2025</h3>
    <p style='color: #000000;'><strong style='color: #0066cc;'>Created by:</strong> Pratik Dalvi, Sushant Marathe, Abhinav Anand, Sushmita Shinde</p>
    <p style='color: #000000;'><strong style='color: #0066cc;'>Mentor:</strong> Prof. Manisha Ghalphade</p>
    <p style='color: #000000;'><strong style='color: #0066cc;'>MIT ADT University, Pune</strong></p>
    <p style='font-size: 0.9em; color: #000000;'>Intelligent note generation powered by AI</p>
</div>
""", unsafe_allow_html=True)
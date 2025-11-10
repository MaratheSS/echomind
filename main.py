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

# Try to import flowchart generation libraries
try:
    import networkx as nx
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    FLOWCHART_AVAILABLE = True
except ImportError:
    FLOWCHART_AVAILABLE = False
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

# Apply cream background with black text theme
st.markdown("""
<style>
    /* Main theme colors - cream background, black text */
    :root {
        --bg-cream: #f5f5dc;
        --bg-cream-light: #fafafa;
        --text-black: #000000;
        --text-dark: #1a1a1a;
        --accent-blue: #0066cc;
        --border-gray: #cccccc;
    }
    
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #f5f5dc 0%, #fafafa 100%);
        color: var(--text-black);
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-black) !important;
    }
    
    /* Main content area */
    .main .block-container {
        background-color: var(--bg-cream);
        color: var(--text-black);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: var(--bg-cream-light) !important;
    }
    
    [data-testid="stSidebar"] .css-1d391kg {
        background-color: var(--bg-cream-light) !important;
    }
    
    /* Text elements */
    p, span, div, label {
        color: var(--text-black) !important;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: var(--accent-blue) !important;
        color: white !important;
        border: none !important;
        border-radius: 5px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        background-color: #0052a3 !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 102, 204, 0.3);
    }
    
    /* Input fields */
    .stTextInput > div > div > input {
        background-color: white !important;
        color: var(--text-black) !important;
        border: 1px solid var(--border-gray) !important;
    }
    
    .stTextInput label {
        color: var(--text-black) !important;
    }
    
    /* File uploader */
    .stFileUploader {
        background-color: white !important;
    }
    
    /* Radio buttons */
    .stRadio > div {
        background-color: white !important;
    }
    
    .stRadio label {
        color: var(--text-black) !important;
    }
    
    /* Selectbox */
    .stSelectbox > div > div > select {
        background-color: white !important;
        color: var(--text-black) !important;
        border: 1px solid var(--border-gray) !important;
    }
    
    /* Info boxes */
    .stInfo {
        background-color: rgba(0, 102, 204, 0.1) !important;
        border-left: 4px solid var(--accent-blue) !important;
        color: var(--text-black) !important;
    }
    
    /* Success messages */
    .stSuccess {
        background-color: rgba(0, 200, 0, 0.1) !important;
        border-left: 4px solid #00c800 !important;
        color: var(--text-black) !important;
    }
    
    /* Error messages */
    .stError {
        background-color: rgba(200, 0, 0, 0.1) !important;
        border-left: 4px solid #c80000 !important;
        color: var(--text-black) !important;
    }
    
    /* Warning messages */
    .stWarning {
        background-color: rgba(255, 191, 0, 0.15) !important;
        border-left: 4px solid #ffbf00 !important;
        color: var(--text-black) !important;
    }
    
    /* Markdown content */
    .stMarkdown {
        color: var(--text-black) !important;
    }
    
    /* Code blocks */
    code {
        background-color: white !important;
        color: var(--accent-blue) !important;
        border: 1px solid var(--border-gray) !important;
    }
    
    /* Tables */
    table {
        background-color: white !important;
        color: var(--text-black) !important;
    }
    
    th {
        background-color: var(--bg-cream-light) !important;
        color: var(--text-black) !important;
        border: 1px solid var(--border-gray) !important;
    }
    
    td {
        border: 1px solid var(--border-gray) !important;
        color: var(--text-black) !important;
    }
    
    /* Dividers */
    hr {
        border-color: var(--border-gray) !important;
    }
    
    /* Form elements */
    .stForm {
        background-color: white !important;
        border: 1px solid var(--border-gray) !important;
        border-radius: 8px !important;
        padding: 20px !important;
    }
</style>
""", unsafe_allow_html=True)

# Set Llama 4 models as constants
OUTLINE_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"
CONTENT_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
      
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

    # def __str__(self):
    #     return (f"\n## {self.get_output_speed():.2f} T/s ⚡\nRound trip time: {self.total_time:.2f}s  Model: {self.model_name}\n\n"
    #             f"| Metric          | Input          | Output          | Total          |\n"
    #             f"|-----------------|----------------|-----------------|----------------|\n"
    #             f"| Speed (T/s)     | {self.get_input_speed():.2f}            | {self.get_output_speed():.2f}            | {(self.input_tokens + self.output_tokens) / self.total_time if self.total_time != 0 else 0:.2f}            |\n"
    #             f"| Tokens          | {self.input_tokens}            | {self.output_tokens}            | {self.input_tokens + self.output_tokens}            |\n"
    #             f"| Inference Time (s) | {self.input_time:.2f}            | {self.output_time:.2f}            | {self.total_time:.2f}            |")

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

def create_pdf_file(content: str, filename: str = "generated_notes"):
    """
    Create a PDF file from the provided content with enhanced formatting.
    Uses md2pdf if available, otherwise falls back to fpdf2.
    """
    if not PDF_AVAILABLE:
        raise RuntimeError("PDF generation is not available on this system. Please use the text download option instead.")
    
    # Try md2pdf first (better formatting)
    if MD2PDF_AVAILABLE:
        try:
            pdf_buffer = BytesIO()
            enhanced_content = _enhance_markdown_for_pdf(content)
            md2pdf(pdf_buffer, md_content=enhanced_content)
            pdf_buffer.seek(0)
            return pdf_buffer
        except Exception as e:
            # If md2pdf fails, try fpdf2 fallback
            if FPDF_AVAILABLE:
                return _create_pdf_with_fpdf(content, filename)
            else:
                raise RuntimeError(f"PDF generation failed: {str(e)}. Please use the text download option instead.")
    
    # Fallback to fpdf2
    if FPDF_AVAILABLE:
        return _create_pdf_with_fpdf(content, filename)
    
    raise RuntimeError("PDF generation is not available on this system. Please use the text download option instead.")

def _enhance_markdown_for_pdf(content: str) -> str:
    """Enhance markdown content for better PDF rendering"""
    # Add header with EchoMind branding
    header = "# EchoMind Generated Notes\n\n---\n\n"
    # Ensure proper spacing
    enhanced = content.replace('\n\n\n', '\n\n')  # Remove excessive line breaks
    return header + enhanced

def _create_pdf_with_fpdf(content: str, filename: str = "generated_notes"):
    """
    Create a PDF file using fpdf2 (fallback method, works on Windows).
    Converts markdown content to properly formatted PDF with headers and sections.
    Handles Unicode characters by removing/escaping unsupported characters.
    """
    import re
    
    def clean_text_for_pdf(text):
        """Remove or replace characters that fpdf2 can't handle"""
        if not text:
            return ""
        # Remove all emojis and special Unicode characters
        # Keep only ASCII printable characters and common punctuation
        cleaned = ""
        for char in text:
            # Check if character is ASCII printable (32-126) or common punctuation
            code = ord(char)
            if 32 <= code <= 126:  # ASCII printable
                cleaned += char
            elif char in ['\n', '\r', '\t']:  # Keep whitespace
                cleaned += char
            elif char in ['—', '–']:  # Replace em dashes with hyphens
                cleaned += '-'
            elif char in ['"', '"', '"', '"']:  # Replace smart quotes
                cleaned += '"'
            elif char in ["'", "'", "'", "'"]:  # Replace smart apostrophes
                cleaned += "'"
            elif char in ['…']:  # Replace ellipsis
                cleaned += '...'
            # Skip all other non-ASCII characters (emojis, special symbols, etc.)
        return cleaned
    
    # Create PDF instance
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Set title font - clean the text first
    pdf.set_font("Arial", "B", 18)
    title = clean_text_for_pdf("EchoMind Generated Notes")
    pdf.cell(0, 12, title, 0, 1, "C")
    pdf.ln(8)
    pdf.set_font("Arial", size=10)
    subtitle = clean_text_for_pdf("Intelligent note generation powered by AI")
    pdf.cell(0, 6, subtitle, 0, 1, "C")
    pdf.ln(10)
    
    # Clean the entire content first to remove all problematic characters
    content = clean_text_for_pdf(content)
    
    # Process content line by line
    lines = content.split('\n')
    pdf.set_font("Arial", size=11)
    
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        
        # Skip empty lines (but add small spacing)
        if not line.strip():
            pdf.ln(4)
            i += 1
            continue
        
        # Handle markdown headers (# Header)
        if line.startswith('#'):
            header_level = len(line) - len(line.lstrip('#'))
            header_text = line.lstrip('#').strip()
            
            if header_text:
                pdf.ln(8)
                # Set font size based on header level
                if header_level == 1:
                    pdf.set_font("Arial", "B", 16)
                elif header_level == 2:
                    pdf.set_font("Arial", "B", 14)
                elif header_level == 3:
                    pdf.set_font("Arial", "B", 12)
                else:
                    pdf.set_font("Arial", "B", 11)
                
                # Ensure header text is clean
                header_text = clean_text_for_pdf(header_text)
                if header_text:
                    pdf.cell(0, 8, header_text, 0, 1)
                    pdf.ln(2)
                pdf.set_font("Arial", size=11)
        
        # Handle markdown bold (**text** or __text__)
        elif re.match(r'^\*\*.*\*\*$', line) or re.match(r'^__.*__$', line):
            bold_text = re.sub(r'\*\*|__', '', line).strip()
            bold_text = clean_text_for_pdf(bold_text)
            if bold_text:
                pdf.set_font("Arial", "B", 11)
                pdf.multi_cell(0, 6, bold_text)
                pdf.set_font("Arial", size=11)
                pdf.ln(2)
        
        # Handle horizontal rules (---)
        elif re.match(r'^-{3,}$', line):
            pdf.ln(5)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
        
        # Handle bullet points and numbered lists
        elif re.match(r'^\s*[-*+]\s+', line) or re.match(r'^\s*\d+\.\s+', line):
            list_text = re.sub(r'^\s*[-*+]\s+', '', line)
            list_text = re.sub(r'^\s*\d+\.\s+', '', list_text)
            list_text = re.sub(r'\*\*|__', '', list_text)  # Remove bold markers
            list_text = clean_text_for_pdf(list_text)
            if list_text.strip():
                pdf.set_x(15)  # Indent for list items
                pdf.multi_cell(0, 6, "- " + list_text.strip())
                pdf.ln(2)
        
        # Regular text content
        else:
            # Clean up markdown formatting
            clean_line = line
            # Remove inline bold/italic
            clean_line = re.sub(r'\*\*([^*]+)\*\*', r'\1', clean_line)
            clean_line = re.sub(r'\*([^*]+)\*', r'\1', clean_line)
            clean_line = re.sub(r'__([^_]+)__', r'\1', clean_line)
            # Remove links but keep text
            clean_line = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean_line)
            # Remove code formatting
            clean_line = re.sub(r'`([^`]+)`', r'\1', clean_line)
            
            # Clean the line for PDF compatibility
            clean_line = clean_text_for_pdf(clean_line)
            
            if clean_line.strip():
                pdf.multi_cell(0, 6, clean_line.strip())
                pdf.ln(2)
        
        i += 1
    
    # Add footer
    pdf.ln(10)
    pdf.set_font("Arial", "I", 9)
    footer = clean_text_for_pdf("Generated by EchoMind - MIT ADT University, Pune (c) 2025")
    pdf.cell(0, 5, footer, 0, 1, "C")
    
    # Save to buffer
    pdf_buffer = BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer

def extract_topics_and_relationships(notes_content: str, model: str = "meta-llama/llama-4-scout-17b-16e-instruct"):
    """
    Extract topics and their relationships from notes content using LLM.
    Returns a dictionary with topics and relationships.
    """
    try:
        # Limit content to avoid token limits
        limited_content = notes_content[:8000]
        prompt = f"""Analyze the following notes and extract:
1. Key topics/concepts mentioned
2. Relationships between topics (what leads to what, dependencies, flow, etc.)

Notes Content:
{limited_content}

Provide your response in JSON format:
{{
    "topics": [
        {{
            "name": "Topic name",
            "description": "Brief description"
        }}
    ],
    "relationships": [
        {{
            "from": "Source topic",
            "to": "Target topic",
            "type": "leads_to|depends_on|part_of|related_to",
            "description": "Brief description of relationship"
        }}
    ]
}}

Focus on the main concepts and how they connect. Create a logical flow or dependency graph."""

        completion = st.session_state.groq.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at analyzing content and extracting topics and their relationships. Create a clear, logical flow of concepts."
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

def generate_flowchart(topics_data: dict, filename: str = "flowchart"):
    """
    Generate a flowchart image from topics and relationships using networkx and matplotlib.
    Returns a BytesIO buffer containing the PNG image.
    """
    if not FLOWCHART_AVAILABLE:
        raise RuntimeError("Flowchart generation libraries are not available. Please install networkx and matplotlib.")
    
    topics = topics_data.get("topics", [])
    relationships = topics_data.get("relationships", [])
    
    if not topics:
        raise ValueError("No topics found to generate flowchart")
    
    # Create a directed graph
    G = nx.DiGraph()
    
    # Add nodes (topics)
    for topic in topics:
        G.add_node(topic["name"], description=topic.get("description", ""))
    
    # Add edges (relationships)
    for rel in relationships:
        from_topic = rel.get("from", "")
        to_topic = rel.get("to", "")
        # Check if topics exist in graph before adding edge
        if from_topic in G.nodes() and to_topic in G.nodes():
            G.add_edge(from_topic, to_topic, 
                      label=rel.get("type", "related_to"),
                      description=rel.get("description", ""))
    
    # If no relationships, create a simple list layout
    if not relationships and len(topics) > 1:
        # Connect topics in order
        for i in range(len(topics) - 1):
            G.add_edge(topics[i]["name"], topics[i+1]["name"], 
                      label="follows", description="")
    
    # Create figure with cream background to match website theme
    fig, ax = plt.subplots(figsize=(16, 12), facecolor='#f5f5dc')
    ax.set_facecolor('#f5f5dc')
    
    # Use hierarchical top-to-bottom layout for clear flow understanding
    try:
        # Try to use hierarchical layout (top to bottom)
        pos = nx.nx_agraph.graphviz_layout(G, prog='dot')
    except:
        # Fallback: Use hierarchical spring layout with better spacing
        try:
            # Calculate levels for hierarchical positioning
            if len(G.nodes()) > 0:
                # Find root nodes (nodes with no incoming edges)
                roots = [n for n in G.nodes() if G.in_degree(n) == 0]
                if not roots:
                    roots = [list(G.nodes())[0]]
                
                # Use multipartite layout for hierarchical structure
                try:
                    pos = nx.multipartite_layout(G, subset_key='level')
                except:
                    # Use spring layout with better parameters for clarity
                    pos = nx.spring_layout(G, k=4, iterations=200, seed=42)
            else:
                pos = nx.spring_layout(G, k=4, iterations=200, seed=42)
        except:
            pos = nx.spring_layout(G, k=4, iterations=200, seed=42)
    
    # Calculate node levels for better color coding (handles cycles)
    def get_node_level(node, visited=None):
        """Calculate the level/depth of a node in the graph"""
        if visited is None:
            visited = set()
        if node in visited:
            return 0  # Cycle detected, return 0
        if G.in_degree(node) == 0:
            return 0  # Root/start node
        
        visited.add(node)
        max_level = 0
        for pred in G.predecessors(node):
            if pred not in visited:
                max_level = max(max_level, get_node_level(pred, visited.copy()))
        visited.remove(node)
        return max_level + 1
    
    node_levels = {node: get_node_level(node) for node in G.nodes()}
    max_level = max(node_levels.values()) if node_levels else 0
    
    # Color nodes by level for visual hierarchy
    def get_node_color(node):
        level = node_levels.get(node, 0)
        if level == 0:
            return '#0066cc'  # Start nodes - accent blue
        elif G.out_degree(node) == 0:
            return '#0052a3'  # End nodes - darker blue
        else:
            # Intermediate nodes - gradient based on level
            intensity = 0.6 + (level / max(max_level, 1)) * 0.3
            return '#4a90e2'  # Medium blue for intermediates
    
    node_colors = [get_node_color(node) for node in G.nodes()]
    
    # Draw nodes with larger size for better readability
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                          node_size=6000, alpha=0.9, 
                          node_shape='s', linewidths=3, 
                          edgecolors='#000000')
    
    # Draw edges with clearer visibility
    nx.draw_networkx_edges(G, pos, edge_color='#666666', 
                          arrows=True, arrowsize=30, 
                          arrowstyle='->', width=3, alpha=0.8,
                          connectionstyle='arc3,rad=0.1')
    
    # Draw labels - improved wrapping for readability
    def wrap_label(text, max_length=18):
        """Wrap long labels to fit in nodes with better formatting"""
        if len(text) <= max_length:
            return text
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            word_len = len(word)
            if current_length + word_len + 1 <= max_length:
                current_line.append(word)
                current_length += word_len + 1
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_len
        if current_line:
            lines.append(' '.join(current_line))
        return '\n'.join(lines)
    
    labels = {node: wrap_label(node, max_length=18) for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=11, 
                           font_weight='bold', font_family='sans-serif',
                           font_color='#ffffff')
    
    # Draw edge labels with better visibility
    edge_labels = {(u, v): d.get('label', '') for u, v, d in G.edges(data=True)}
    # Only show edge labels if they're meaningful
    meaningful_edge_labels = {k: v for k, v in edge_labels.items() if v and v != 'related_to' and v != 'follows'}
    if meaningful_edge_labels:
        nx.draw_networkx_edge_labels(G, pos, meaningful_edge_labels, font_size=9, 
                                    font_color='#000000', alpha=0.95, font_weight='bold',
                                    bbox=dict(boxstyle='round,pad=0.5', facecolor='#ffffff', 
                                             edgecolor='#0066cc', linewidth=2, alpha=0.95))
    
    # Add title with website theme styling
    plt.title("Topic Flowchart - EchoMind", fontsize=20, fontweight='bold', 
              pad=30, color='#000000', family='sans-serif')
    
    # Remove axes
    ax.axis('off')
    plt.tight_layout(pad=3.0)
    
    # Save to buffer with cream background
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight', 
                facecolor='#f5f5dc', edgecolor='none', transparent=False)
    img_buffer.seek(0)
    plt.close(fig)
    
    return img_buffer

def generate_architecture_diagram(topics_data: dict, filename: str = "architecture_diagram"):
    """
    Generate an architecture diagram from topics and relationships using networkx and matplotlib.
    Returns a BytesIO buffer containing the PNG image.
    Similar to flowchart but with architecture-focused styling and layout.
    """
    if not FLOWCHART_AVAILABLE:
        raise RuntimeError("Architecture diagram generation libraries are not available. Please install networkx and matplotlib.")
    
    topics = topics_data.get("topics", [])
    relationships = topics_data.get("relationships", [])
    
    if not topics:
        raise ValueError("No topics found to generate architecture diagram")
    
    # Create a directed graph
    G = nx.DiGraph()
    
    # Add nodes (topics)
    for topic in topics:
        G.add_node(topic["name"], description=topic.get("description", ""))
    
    # Add edges (relationships)
    for rel in relationships:
        from_topic = rel.get("from", "")
        to_topic = rel.get("to", "")
        # More lenient matching - check if topics exist in graph
        if from_topic in G.nodes() and to_topic in G.nodes():
            G.add_edge(from_topic, to_topic, 
                      label=rel.get("type", "related_to"),
                      description=rel.get("description", ""))
    
    # If no relationships, create a hierarchical layout
    if not relationships and len(topics) > 1:
        # Connect topics in a hierarchical manner
        for i in range(len(topics) - 1):
            G.add_edge(topics[i]["name"], topics[i+1]["name"], 
                      label="contains", description="")
    
    # Create figure with larger size and cream background for architecture diagrams
    fig, ax = plt.subplots(figsize=(18, 14), facecolor='#f5f5dc')
    ax.set_facecolor('#f5f5dc')
    
    # Use hierarchical layout for architecture diagrams - top to bottom flow
    try:
        # Try hierarchical layout first
        pos = nx.nx_agraph.graphviz_layout(G, prog='dot')
    except:
        # Fallback: Use hierarchical spring layout with maximum spacing
        try:
            # Calculate levels for better hierarchical positioning
            if len(G.nodes()) > 0:
                try:
                    pos = nx.multipartite_layout(G, subset_key='level')
                except:
                    # Use spring layout with maximum spacing for clarity
                    pos = nx.spring_layout(G, k=5, iterations=300, seed=42)
            else:
                pos = nx.spring_layout(G, k=5, iterations=300, seed=42)
        except:
            pos = nx.spring_layout(G, k=5, iterations=300, seed=42)
    
    # Calculate node levels for visual hierarchy (handles cycles)
    def get_node_level(node, visited=None):
        """Calculate the level/depth of a node in the graph"""
        if visited is None:
            visited = set()
        if node in visited:
            return 0  # Cycle detected, return 0
        if G.in_degree(node) == 0:
            return 0  # Root/start node
        
        visited.add(node)
        max_level = 0
        for pred in G.predecessors(node):
            if pred not in visited:
                max_level = max(max_level, get_node_level(pred, visited.copy()))
        visited.remove(node)
        return max_level + 1
    
    node_levels = {node: get_node_level(node) for node in G.nodes()}
    max_level = max(node_levels.values()) if node_levels else 0
    
    # Color nodes by level for clear architecture visualization
    def get_node_color(node):
        level = node_levels.get(node, 0)
        if level == 0:
            return '#0066cc'  # Base/entry components - accent blue
        elif G.out_degree(node) == 0:
            return '#0052a3'  # Final/output components - darker blue
        else:
            return '#4a90e2'  # Intermediate components - medium blue
    
    node_colors = [get_node_color(node) for node in G.nodes()]
    
    # Draw nodes with larger size for architecture clarity
    nx.draw_networkx_nodes(G, pos, node_color=node_colors,
                          node_size=7000, alpha=0.92, 
                          node_shape='s', linewidths=3.5, 
                          edgecolors='#000000')
    
    # Draw edges with clear architecture-style visibility
    nx.draw_networkx_edges(G, pos, edge_color='#666666', 
                          arrows=True, arrowsize=35, 
                          arrowstyle='->', width=3.5, alpha=0.85,
                          connectionstyle='arc3,rad=0.12')
    
    # Draw labels - improved wrapping for architecture readability
    def wrap_label(text, max_length=20):
        """Wrap long labels to fit in nodes with better formatting"""
        if len(text) <= max_length:
            return text
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            word_len = len(word)
            if current_length + word_len + 1 <= max_length:
                current_line.append(word)
                current_length += word_len + 1
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_len
        if current_line:
            lines.append(' '.join(current_line))
        return '\n'.join(lines)
    
    labels = {node: wrap_label(node, max_length=20) for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=12, 
                           font_weight='bold', font_family='sans-serif',
                           font_color='#ffffff')
    
    # Draw edge labels with enhanced visibility for architecture
    edge_labels = {(u, v): d.get('label', '') for u, v, d in G.edges(data=True)}
    # Only show meaningful edge labels
    meaningful_edge_labels = {k: v for k, v in edge_labels.items() if v and v != 'related_to' and v != 'contains'}
    if meaningful_edge_labels:
        nx.draw_networkx_edge_labels(G, pos, meaningful_edge_labels, font_size=10, 
                                    font_color='#000000', alpha=0.95, font_weight='bold',
                                    bbox=dict(boxstyle='round,pad=0.6', facecolor='#ffffff', 
                                             edgecolor='#0066cc', linewidth=2.5, alpha=0.95))
    
    # Add title with website theme styling
    plt.title("Architecture Diagram - EchoMind", fontsize=22, fontweight='bold', 
              pad=35, color='#000000', family='sans-serif')
    
    # Remove axes
    ax.axis('off')
    plt.tight_layout(pad=3.5)
    
    # Save to buffer with cream background
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight',
                facecolor='#f5f5dc', edgecolor='none', transparent=False)
    img_buffer.seek(0)
    plt.close(fig)
    
    return img_buffer

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

def transcribe_audio(audio_file):
    """
    Transcribes audio using Groq's Whisper API.
    """
    transcription = st.session_state.groq.audio.transcriptions.create(
      file=audio_file,
      model="whisper-large-v3",
      prompt="",
      response_format="json",
      language="en",
      temperature=0.0 
    )

    results = transcription.text
    return results

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

def generate_notes_structure(transcript: str, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
    """
    Returns notes structure content as well as total tokens and total time for generation.
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
    completion = st.session_state.groq.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Write in JSON format:\n\n{\"Title of section goes here\":\"Description of section goes here\",\"Title of section goes here\":\"Description of section goes here\",\"Title of section goes here\":\"Description of section goes here\"}"
            },
            {
                "role": "user",
                "content": f"### Transcript {transcript}\n\n### Example\n\n{shot_example}### Instructions\n\nCreate a structure for comprehensive notes on the above transcribed audio. Section titles and content descriptions must be comprehensive. Quality over quantity."
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

def generate_section(transcript: str, existing_notes: str, section: str, model: str = "meta-llama/llama-4-scout-17b-16e-instruct"):
    stream = st.session_state.groq.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an expert writer. Generate comprehensive note content for the section provided based factually on the transcript provided. Do *not* repeat any content from previous sections. Do *not* include the section title/header in your response - only generate the content."
            },
            {
                "role": "user",
                "content": f"### Transcript\n\n{transcript}\n\n### Existing Notes\n\n{existing_notes}\n\n### Instructions\n\nGenerate comprehensive note content (without the section title) for this section only based on the transcript: \n\n{section}"
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

st.write("""
# EchoMind: Create structured notes from audio 
""")

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
        st.write(f"# 🧠 EchoMind \n## Generate notes from audio in seconds using Groq, Whisper, and Llama")
        st.markdown(f"**EchoMind** - Intelligent note generation powered by AI\n\nAs with all generative AI, content may include inaccurate or placeholder information. EchoMind is in beta and all feedback is welcome!")
        
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
            st.info("📝 No saved notes till yet. Generate notes to see them here!")
        
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
    
    # TTS and Recording Section
    if "notes" in st.session_state:
        st.markdown("---")
        st.markdown("### 🔊 Audio Features")
        col1, col2 = st.columns(2)
        
        with col1:
            # Text-to-Speech Button
            notes_text = get_notes_text_for_tts()
            if notes_text:
                # Clean and escape text for JavaScript
                clean_text = notes_text[:8000]  # Limit length
                # Escape for JavaScript string
                clean_text = clean_text.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$').replace('\n', '\\n').replace('\r', '\\r')
                
                # Create HTML with embedded JavaScript for Web Speech API
                tts_html = f"""
                <div id="tts-container">
                    <button onclick="speakNotes()" style="padding: 10px 20px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;">
                        🎧 Play Notes
                    </button>
                    <button onclick="stopSpeaking()" style="padding: 10px 20px; background-color: #f44336; color: white; border: none; border-radius: 5px; cursor: pointer; margin-left: 10px;">
                        ⏹️ Stop
                    </button>
                </div>
                <script>
                    const notesText = `{clean_text}`;
                    
                    function speakNotes() {{
                        if ('speechSynthesis' in window) {{
                            const utterance = new SpeechSynthesisUtterance(notesText);
                            utterance.rate = 0.9;
                            utterance.pitch = 1.0;
                            utterance.volume = 1.0;
                            utterance.lang = 'en-US';
                            window.speechSynthesis.speak(utterance);
                        }} else {{
                            alert('Text-to-speech is not supported in your browser. Please use a modern browser like Chrome, Edge, or Safari.');
                        }}
                    }}
                    
                    function stopSpeaking() {{
                        if ('speechSynthesis' in window) {{
                            window.speechSynthesis.cancel();
                        }}
                    }}
                </script>
                """
                st.markdown(tts_html, unsafe_allow_html=True)
                st.info("💡 Click 'Play Notes' button above to hear your notes read aloud")
            else:
                st.warning("No notes available to read. Generate notes first.")
        
        with col2:
            # Real-time Recording Info
            st.info("💡 Use the audio recorder below or upload a pre-recorded audio file to generate notes from live lectures")

    # Real-time audio recording option (outside form for better UX)
    st.markdown("---")
    st.markdown("### 🎤 Record Live Audio")
    
    # Initialize recording state
    if 'recording_active' not in st.session_state:
        st.session_state.recording_active = False
    if 'recording_time' not in st.session_state:
        st.session_state.recording_time = 0
    
    # Try to use audio_input if available (Streamlit native feature)
    try:
        if hasattr(st, 'audio_input'):
            audio_bytes = st.audio_input("Record your lecture in real-time", key="live_recording")
            if audio_bytes:
                st.session_state.uploaded_filename = "live_recording.wav"
                st.session_state.live_audio_bytes = audio_bytes
                st.success("✅ Recording captured! Click 'Generate Notes' below to process.")
        else:
            # Enhanced JavaScript-based audio recorder with timer and direct upload
            recorder_container = st.container()
            with recorder_container:
                st.markdown("""
                <div id="audio-recorder-container" style="background-color: white; padding: 20px; border-radius: 10px; border: 2px solid #cccccc; margin: 10px 0;">
                    <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 15px;">
                        <button id="start-recording" style="padding: 12px 24px; background-color: #0066cc; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: 600; transition: all 0.3s;">
                            🎤 Start Recording
                        </button>
                        <button id="stop-recording" style="padding: 12px 24px; background-color: #f44336; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: 600; display: none; transition: all 0.3s;">
                            ⏹️ Stop Recording
                        </button>
                        <button id="clear-recording" style="padding: 12px 24px; background-color: #666666; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: 600; display: none;">
                            🗑️ Clear
                        </button>
                    </div>
                    <div id="recording-status" style="margin: 15px 0; padding: 15px; border-radius: 5px; background-color: #fafafa; border-left: 4px solid #0066cc; display: none;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span id="recording-indicator" style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: #f44336; animation: pulse 1.5s infinite;"></span>
                            <span id="recording-text" style="font-weight: 600; color: #000000; font-size: 16px;">Recording...</span>
                            <span id="recording-timer" style="margin-left: auto; font-weight: 600; color: #0066cc; font-size: 16px; font-family: monospace;">00:00</span>
                        </div>
                    </div>
                    <div id="recording-complete" style="margin: 15px 0; padding: 15px; border-radius: 5px; background-color: #e8f5e9; border-left: 4px solid #4CAF50; display: none;">
                        <p style="color: #2e7d32; font-weight: 600; margin: 0 0 10px 0;">✅ Recording complete!</p>
                        <audio id="audio-playback" controls style="width: 100%; margin: 10px 0;"></audio>
                        <p style="color: #000000; font-size: 14px; margin: 10px 0 0 0;">Your recording is ready. Click "Generate Notes" below to process it.</p>
                    </div>
                    <div id="recording-error" style="margin: 15px 0; padding: 15px; border-radius: 5px; background-color: #ffebee; border-left: 4px solid #f44336; display: none;">
                        <p style="color: #c62828; font-weight: 600; margin: 0;" id="error-message"></p>
                    </div>
                </div>
                <style>
                    @keyframes pulse {
                        0%, 100% { opacity: 1; }
                        50% { opacity: 0.5; }
                    }
                    #start-recording:hover { background-color: #0052a3 !important; transform: translateY(-2px); }
                    #stop-recording:hover { background-color: #d32f2f !important; transform: translateY(-2px); }
                    #clear-recording:hover { background-color: #424242 !important; transform: translateY(-2px); }
                </style>
                <script>
                    (function() {
                        let mediaRecorder;
                        let audioChunks = [];
                        let audioBlob;
                        let recordingTimer;
                        let recordingSeconds = 0;
                        let audioContext;
                        let analyser;
                        let dataArray;
                        
                        const startBtn = document.getElementById('start-recording');
                        const stopBtn = document.getElementById('stop-recording');
                        const clearBtn = document.getElementById('clear-recording');
                        const statusDiv = document.getElementById('recording-status');
                        const completeDiv = document.getElementById('recording-complete');
                        const errorDiv = document.getElementById('recording-error');
                        const recordingText = document.getElementById('recording-text');
                        const recordingTimer = document.getElementById('recording-timer');
                        const audioPlayback = document.getElementById('audio-playback');
                        
                        function formatTime(seconds) {
                            const mins = Math.floor(seconds / 60);
                            const secs = seconds % 60;
                            return String(mins).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
                        }
                        
                        function updateTimer() {
                            recordingSeconds++;
                            recordingTimer.textContent = formatTime(recordingSeconds);
                        }
                        
                        function resetUI() {
                            startBtn.style.display = 'inline-block';
                            stopBtn.style.display = 'none';
                            clearBtn.style.display = 'none';
                            statusDiv.style.display = 'none';
                            completeDiv.style.display = 'none';
                            errorDiv.style.display = 'none';
                            audioPlayback.style.display = 'none';
                            recordingSeconds = 0;
                            if (recordingTimer) {
                                clearInterval(recordingTimer);
                            }
                        }
                        
                        startBtn.addEventListener('click', async () => {
                            try {
                                errorDiv.style.display = 'none';
                                const stream = await navigator.mediaDevices.getUserMedia({ 
                                    audio: {
                                        echoCancellation: true,
                                        noiseSuppression: true,
                                        autoGainControl: true,
                                        sampleRate: 44100
                                    } 
                                });
                                
                                // Determine best MIME type
                                const options = { mimeType: 'audio/webm' };
                                if (!MediaRecorder.isTypeSupported('audio/webm')) {
                                    options.mimeType = 'audio/mp4';
                                }
                                if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                                    options.mimeType = 'audio/ogg';
                                }
                                
                                mediaRecorder = new MediaRecorder(stream, options);
                                audioChunks = [];
                                
                                mediaRecorder.ondataavailable = (event) => {
                                    if (event.data.size > 0) {
                                        audioChunks.push(event.data);
                                    }
                                };
                                
                                mediaRecorder.onstop = () => {
                                    audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType });
                                    const audioUrl = URL.createObjectURL(audioBlob);
                                    audioPlayback.src = audioUrl;
                                    audioPlayback.style.display = 'block';
                                    
                                    // Determine file extension based on MIME type
                                    let fileExt = 'webm';
                                    if (mediaRecorder.mimeType.includes('mp4')) fileExt = 'mp4';
                                    else if (mediaRecorder.mimeType.includes('ogg')) fileExt = 'ogg';
                                    else if (mediaRecorder.mimeType.includes('wav')) fileExt = 'wav';
                                    
                                    // Auto-download the recording
                                    const downloadUrl = URL.createObjectURL(audioBlob);
                                    const a = document.createElement('a');
                                    a.href = downloadUrl;
                                    a.download = 'live_recording.' + fileExt;
                                    document.body.appendChild(a);
                                    a.click();
                                    document.body.removeChild(a);
                                    
                                    // Store blob in window for potential future use
                                    window.recordedAudioBlob = audioBlob;
                                    window.recordedAudioMimeType = mediaRecorder.mimeType;
                                    
                                    // Update UI
                                    statusDiv.style.display = 'none';
                                    completeDiv.style.display = 'block';
                                    startBtn.style.display = 'inline-block';
                                    stopBtn.style.display = 'none';
                                    clearBtn.style.display = 'inline-block';
                                    
                                    // Stop timer
                                    if (recordingTimer) {
                                        clearInterval(recordingTimer);
                                    }
                                    
                                    // Update completion message with file info
                                    const completeMessage = completeDiv.querySelector('p:last-child');
                                    if (completeMessage) {
                                        completeMessage.textContent = 'Recording downloaded automatically! Upload it using the file uploader above or below, then click "Generate Notes".';
                                    }
                                };
                                
                                mediaRecorder.onerror = (event) => {
                                    errorDiv.style.display = 'block';
                                    document.getElementById('error-message').textContent = 'Recording error: ' + event.error;
                                    resetUI();
                                };
                                
                                // Start recording
                                mediaRecorder.start(1000); // Collect data every second
                                recordingSeconds = 0;
                                recordingTimer = setInterval(updateTimer, 1000);
                                
                                // Update UI
                                startBtn.style.display = 'none';
                                stopBtn.style.display = 'inline-block';
                                clearBtn.style.display = 'none';
                                statusDiv.style.display = 'block';
                                completeDiv.style.display = 'none';
                                recordingText.textContent = 'Recording...';
                                recordingTimer.textContent = '00:00';
                                
                            } catch (err) {
                                errorDiv.style.display = 'block';
                                document.getElementById('error-message').textContent = 'Error: ' + err.message + '. Please allow microphone access.';
                                resetUI();
                            }
                        });
                        
                        stopBtn.addEventListener('click', () => {
                            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                                mediaRecorder.stop();
                                mediaRecorder.stream.getTracks().forEach(track => track.stop());
                            }
                        });
                        
                        clearBtn.addEventListener('click', () => {
                            if (audioBlob) {
                                URL.revokeObjectURL(audioPlayback.src);
                                audioBlob = null;
                                window.recordedAudioBlob = null;
                                resetUI();
                            }
                        });
                    })();
                </script>
                """, unsafe_allow_html=True)
                
                # Add a file uploader that can be used to upload the recorded audio
                st.markdown("---")
                st.markdown("#### 📤 Upload Your Recording")
                uploaded_audio = st.file_uploader(
                    "After recording, download the file and upload it here (or use the file uploader below)",
                    type=["webm", "mp4", "ogg", "wav", "mp3", "m4a"],
                    key="recorded_audio_upload"
                )
                
                if uploaded_audio:
                    # Convert UploadedFile to bytes
                    uploaded_audio.seek(0)
                    audio_bytes = uploaded_audio.read()
                    st.session_state.live_audio_bytes = audio_bytes
                    st.session_state.uploaded_filename = uploaded_audio.name
                    st.success("✅ Recording uploaded! Click 'Generate Notes' below to process.")
                
                st.info("💡 **How to use:**\n1. Click 'Start Recording' to begin (browser will ask for microphone permission)\n2. Speak your lecture - watch the timer!\n3. Click 'Stop Recording' when done\n4. The recording will automatically download\n5. Upload the downloaded file using the file uploader above or in the form below\n6. Click 'Generate Notes' to process your recording")
    except Exception as e:
        # Ultimate fallback: just show instructions
        st.warning(f"⚠️ Audio recording feature unavailable: {str(e)}")
        st.info("""
        **🎤 To record live audio:**
        1. Use your device's voice recorder app or browser extension
        2. Record your lecture
        3. Save the file (WAV, MP3, or M4A format)
        4. Upload it using the file uploader below
        """)
    
    st.markdown("---")
    input_method = st.radio("Choose input method:", ["Upload audio file", "YouTube link"])
    audio_file = None
    youtube_link = None
    
    # Check if API key is set
    if not GROQ_API_KEY:
        st.error("⚠️ GROQ_API_KEY not found in environment variables. Please set it in your `.env` or `example.env` file.")
        st.stop()
    
    with st.form("groqform"):
        # Add radio button to choose between file upload and YouTube link
        
        if input_method == "Upload audio file":
            audio_file = st.file_uploader("Upload an audio file", type=["mp3", "wav", "m4a", "webm", "mp4", "ogg"]) # TODO: Add a max size
            if audio_file:
                # Store filename for PDF export
                st.session_state.uploaded_filename = audio_file.name
                # Convert UploadedFile to BytesIO for transcription
                if hasattr(audio_file, 'read'):
                    audio_file.seek(0)
                    audio_bytes = audio_file.read()
                    audio_file = BytesIO(audio_bytes)
                    audio_file.name = st.session_state.uploaded_filename
        else:
            youtube_link = st.text_input("Enter YouTube link:", "")

        # Generate button
        submitted = st.form_submit_button(st.session_state.button_text, on_click=disable, disabled=st.session_state.button_disabled)

        #processing status
        status_text = st.empty()
        def display_status(text):
            status_text.write(text)

        def clear_status():
            status_text.empty()

        download_status_text = st.empty()
        def display_download_status(text:str):
            download_status_text.write(text)    

        def clear_download_status():
            download_status_text.empty()
        
        # Statistics
        placeholder = st.empty()
        def display_statistics():
            with placeholder.container():
                if st.session_state.statistics_text:
                    if "Transcribing audio in background" not in st.session_state.statistics_text:
                        st.markdown(st.session_state.statistics_text + "\n\n---\n")  # Format with line if showing statistics
                    else:
                        st.markdown(st.session_state.statistics_text)
                else:
                    placeholder.empty()

        if submitted:
            # Check for live recording first
            if st.session_state.get('live_audio_bytes'):
                # Handle both bytes and UploadedFile objects
                live_audio = st.session_state.live_audio_bytes
                if hasattr(live_audio, 'read'):
                    # It's an UploadedFile, read the bytes
                    live_audio.seek(0)
                    audio_bytes = live_audio.read()
                else:
                    # It's already bytes
                    audio_bytes = live_audio
                
                audio_file = BytesIO(audio_bytes)
                audio_file.name = st.session_state.get('uploaded_filename', "live_recording.wav")
                st.session_state.uploaded_filename = audio_file.name
                input_method = "Upload audio file"  # Treat as uploaded file
                st.session_state.live_audio_bytes = None  # Clear after use
            
            if input_method == "Upload audio file" and audio_file is None:
                st.error("Please upload an audio file or record live audio")
            elif input_method == "YouTube link" and not youtube_link:
                st.error("Please enter a YouTube link")
            else:
                st.session_state.button_disabled = True
                # Show temporary message before transcription is generated and statistics show
            
            audio_file_path = None

            if input_method == "YouTube link":
                display_status("Downloading audio from YouTube link ....")
                audio_file_path = download_video_audio(youtube_link, display_download_status)
                if audio_file_path is None:
                    st.error("Failed to download audio from YouTube link. Please try again.")
                    enable()
                    clear_status()
                else:
                    # Read the downloaded file and create a file-like objec
                    display_status("Processing Youtube audio ....")
                    with open(audio_file_path, 'rb') as f:
                        file_contents = f.read()
                    audio_file = BytesIO(file_contents)

                    # Check size first to ensure will work with Whisper
                    if os.path.getsize(audio_file_path) > MAX_FILE_SIZE:
                        raise ValueError(FILE_TOO_LARGE_MESSAGE)

                    audio_file.name = os.path.basename(audio_file_path)  # Set the file name
                    delete_download(audio_file_path)
                clear_download_status()

            # API key is already set from environment variables

            display_status("Transcribing audio in background....")
            transcription_text = transcribe_audio(audio_file)

            display_statistics()
            
            # Identify speakers
            display_status("Identifying speakers and analyzing conversation....")
            speaker_info = identify_speakers(transcription_text, model=CONTENT_MODEL)
            st.session_state.speaker_info = speaker_info

            display_status("Generating notes structure....")
            large_model_generation_statistics, notes_structure = generate_notes_structure(transcription_text, model=OUTLINE_MODEL)
            print("Structure: ",notes_structure)

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
                            content_stream = generate_section(transcript=transcription_text, existing_notes=notes.return_existing_contents(), section=(title + ": " + content), model=CONTENT_MODEL)
                            for chunk in content_stream:
                                # Check if GenerationStatistics data is returned instead of str tokens
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
            
            # Save notes to database after generation is complete
            if 'notes' in st.session_state:
                try:
                    notes_content = st.session_state.notes.get_markdown_content()
                    filename = st.session_state.get('uploaded_filename', 'generated_notes')
                    # Create a title from filename or use a default
                    title = os.path.splitext(filename)[0] if filename else "Untitled Notes"
                    title = title.replace('_', ' ').replace('-', ' ').title()
                    
                    # Save to database
                    note_id = save_note_to_db(title, filename, notes_content)
                    if note_id:
                        st.success(f"✅ Notes saved to database! (ID: {note_id})")
                    else:
                        st.warning("⚠️ Notes generated but could not be saved to database.")
                except Exception as e:
                    st.warning(f"Could not save notes to database: {str(e)}")
            
            # Clear flowchart and architecture diagram state when new notes are generated
            if 'flowchart_data' in st.session_state:
                del st.session_state.flowchart_data
            if 'flowchart_image' in st.session_state:
                del st.session_state.flowchart_image
            if 'flowchart_generated' in st.session_state:
                del st.session_state.flowchart_generated
            if 'architecture_diagram_image' in st.session_state:
                del st.session_state.architecture_diagram_image
            if 'architecture_diagram_generated' in st.session_state:
                del st.session_state.architecture_diagram_generated

except Exception as e:
    st.session_state.button_disabled = False

    if hasattr(e, 'status_code') and e.status_code == 413:
        # In the future, this limitation will be fixed as EchoMind will automatically split the audio file and transcribe each part.
        st.error(FILE_TOO_LARGE_MESSAGE)
    else:
        st.error(e)

    if st.button("Clear"):
        st.rerun()
    
    # Remove audio after exception to prevent data storage leak
    if audio_file_path is not None:
        delete_download(audio_file_path)

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
            if 'flowchart_image' not in st.session_state or not st.session_state.get('flowchart_generated', False):
                with st.spinner("🎨 Generating flowchart visualization..."):
                    try:
                        flowchart_img = generate_flowchart(flowchart_data)
                        st.session_state.flowchart_image = flowchart_img
                        st.session_state.flowchart_generated = True
                    except Exception as e:
                        st.error(f"Error generating flowchart: {str(e)}")
                        st.session_state.flowchart_image = None
            
            # Display flowchart
            flowchart_image = st.session_state.get('flowchart_image')
            if flowchart_image:
                flowchart_image.seek(0)
                st.image(flowchart_image, caption="Topic Flowchart - Visual representation of concepts and their relationships")
                
                # Download flowchart button
                base_filename = st.session_state.get('uploaded_filename', 'generated_notes')
                if base_filename.endswith(('.mp3', '.wav', '.m4a', '.webm')):
                    base_filename = os.path.splitext(base_filename)[0]
                base_filename = "".join(c for c in base_filename if c.isalnum() or c in (' ', '-', '_')).strip()
                if not base_filename:
                    base_filename = 'generated_notes'
                
                flowchart_image.seek(0)
                st.download_button(
                    label='📥 Download Flowchart (.png)',
                    data=flowchart_image,
                    file_name=f'{base_filename}_flowchart.png',
                    mime='image/png',
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
        st.info("📊 Flowchart generation requires networkx and matplotlib libraries. Please install them to use this feature.")

# Architecture Diagram section - generate and display architecture diagram
if "notes" in st.session_state:
    st.markdown("---")
    st.markdown("### 🏗️ Architecture Diagram")
    
    if FLOWCHART_AVAILABLE:
        # Use the same flowchart_data for architecture diagram
        flowchart_data = st.session_state.get('flowchart_data')
        if flowchart_data and flowchart_data.get("topics"):
            if 'architecture_diagram_image' not in st.session_state or not st.session_state.get('architecture_diagram_generated', False):
                with st.spinner("🎨 Generating architecture diagram visualization..."):
                    try:
                        architecture_img = generate_architecture_diagram(flowchart_data)
                        st.session_state.architecture_diagram_image = architecture_img
                        st.session_state.architecture_diagram_generated = True
                    except Exception as e:
                        st.error(f"Error generating architecture diagram: {str(e)}")
                        st.session_state.architecture_diagram_image = None
            
            # Display architecture diagram
            architecture_image = st.session_state.get('architecture_diagram_image')
            if architecture_image:
                architecture_image.seek(0)
                st.image(architecture_image, caption="Architecture Diagram - Visual representation of system architecture and component relationships")
                
                # Download architecture diagram button
                base_filename = st.session_state.get('uploaded_filename', 'generated_notes')
                if base_filename.endswith(('.mp3', '.wav', '.m4a', '.webm')):
                    base_filename = os.path.splitext(base_filename)[0]
                base_filename = "".join(c for c in base_filename if c.isalnum() or c in (' ', '-', '_')).strip()
                if not base_filename:
                    base_filename = 'generated_notes'
                
                architecture_image.seek(0)
                st.download_button(
                    label='📥 Download Architecture Diagram (.png)',
                    data=architecture_image,
                    file_name=f'{base_filename}_architecture_diagram.png',
                    mime='image/png',
                    key='download_architecture_diagram'
                )
            else:
                st.info("Architecture diagram generation in progress...")
        else:
            if flowchart_data is None:
                st.info("🏗️ Architecture diagram data not available. Please wait for topic extraction to complete.")
            else:
                st.info("🏗️ No topics found to generate architecture diagram. Make sure your notes contain clear topics and concepts.")
    else:
        st.info("🏗️ Architecture diagram generation requires networkx and matplotlib libraries. Please install them to use this feature.")

# Download section - outside form (Streamlit requirement: download buttons can't be in forms)
if "notes" in st.session_state:
    st.markdown("---")
    st.markdown("### 📥 Download Your Notes")
    
    # Get filename from uploaded file or use default
    base_filename = st.session_state.get('uploaded_filename', 'generated_notes')
    if base_filename.endswith(('.mp3', '.wav', '.m4a', '.webm')):
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
                pdf_file = create_pdf_file(st.session_state.notes.get_markdown_content(), base_filename)
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

# Footer with creator information
st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 20px; background-color: white; border-radius: 10px; margin-top: 30px; border: 1px solid #cccccc;'>
    <h3 style='color: #0066cc; margin-top: 0;'>🧠 EchoMind © 2025</h3>
    <p style='color: #000000;'><strong style='color: #0066cc;'>Created by:</strong> Pratik Dalvi, Sushant Marathe, Abhinav Anand, Sushmita Shinde</p>
    <p style='color: #000000;'><strong style='color: #0066cc;'>Mentor:</strong> Prof Dr. Manisha Galphade</p>
    <p style='color: #000000;'><strong style='color: #0066cc;'>MIT ADT University, Pune</strong></p>
    <p style='font-size: 0.9em; color: #000000;'>Intelligent note generation powered by AI</p>
</div>
""", unsafe_allow_html=True)

"""
Sentiment Analysis module for EchoMind.
"""
import json
import re

def analyze_sentiment_with_groq(text: str, groq_client, model: str = "llama-3.3-70b-versatile") -> dict:
    """Analyze sentiment using Groq LLM"""
    try:
        limited_text = text[:6000]
        
        prompt = f"""Analyze the sentiment and emotional tone of the following text. Provide:
1. Overall sentiment (positive, negative, neutral, mixed)
2. Sentiment score (-1.0 to 1.0)
3. Dominant emotions detected
4. Tone analysis
5. Key emotional phrases

Text:
{limited_text}

Respond in JSON format:
{{
    "overall_sentiment": "positive|negative|neutral|mixed",
    "sentiment_score": 0.0,
    "confidence": 0.0,
    "dominant_emotions": ["emotion1", "emotion2"],
    "tone": "formal|informal|academic|conversational|technical|motivational",
    "emotional_highlights": [
        {{
            "text": "quote from the text",
            "emotion": "emotion type",
            "intensity": "low|medium|high"
        }}
    ],
    "summary": "Brief sentiment summary in 1-2 sentences"
}}"""

        completion = groq_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert sentiment and emotion analyst. Provide accurate, nuanced analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        result = json.loads(completion.choices[0].message.content)
        return result
        
    except Exception as e:
        # Fallback to basic analysis
        return analyze_sentiment_basic(text)


def analyze_sentiment_basic(text: str) -> dict:
    """Basic sentiment analysis without external dependencies"""
    try:
        from textblob import TextBlob
        
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        if polarity > 0.1:
            sentiment = "positive"
        elif polarity < -0.1:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        if subjectivity < 0.3:
            tone = "objective/formal"
        elif subjectivity < 0.6:
            tone = "balanced"
        else:
            tone = "subjective/informal"
        
        highlights = []
        for sentence in blob.sentences[:10]:
            sp = sentence.sentiment.polarity
            if abs(sp) > 0.3:
                highlights.append({
                    "text": str(sentence)[:100],
                    "emotion": "positive" if sp > 0 else "negative",
                    "intensity": "high" if abs(sp) > 0.6 else "medium"
                })
        
        return {
            "overall_sentiment": sentiment,
            "sentiment_score": round(polarity, 3),
            "confidence": round(1 - subjectivity * 0.5, 3),
            "dominant_emotions": [sentiment],
            "tone": tone,
            "emotional_highlights": highlights[:5],
            "summary": f"The text has a {sentiment} tone with {'high' if subjectivity > 0.6 else 'moderate' if subjectivity > 0.3 else 'low'} subjectivity."
        }
    except ImportError:
        # Even more basic fallback - no TextBlob needed
        positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'best', 'love', 'happy', 'success', 'perfect', 'brilliant']
        negative_words = ['bad', 'terrible', 'awful', 'worst', 'hate', 'failure', 'poor', 'horrible', 'wrong', 'problem', 'difficult']
        
        text_lower = text.lower()
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        
        if pos_count > neg_count:
            sentiment = "positive"
            score = min(pos_count * 0.1, 1.0)
        elif neg_count > pos_count:
            sentiment = "negative"
            score = max(-neg_count * 0.1, -1.0)
        else:
            sentiment = "neutral"
            score = 0.0
        
        return {
            "overall_sentiment": sentiment,
            "sentiment_score": score,
            "confidence": 0.5,
            "dominant_emotions": [sentiment],
            "tone": "unknown",
            "emotional_highlights": [],
            "summary": f"Basic analysis suggests {sentiment} sentiment."
        }


def get_sentiment_emoji(sentiment: str) -> str:
    mapping = {
        "positive": "😊", "negative": "😞", "neutral": "😐",
        "mixed": "🤔", "unknown": "❓"
    }
    return mapping.get(sentiment.lower(), "❓")


def get_sentiment_color(score: float) -> str:
    if score > 0.3: return "#10b981"
    elif score > 0.1: return "#84cc16"
    elif score > -0.1: return "#6b7280"
    elif score > -0.3: return "#f59e0b"
    else: return "#ef4444"


def render_sentiment_display(sentiment_data: dict):
    """Render sentiment analysis results in Streamlit"""
    import streamlit as st
    
    overall = sentiment_data.get("overall_sentiment", "unknown")
    score = sentiment_data.get("sentiment_score", 0)
    confidence = sentiment_data.get("confidence", 0)
    emotions = sentiment_data.get("dominant_emotions", [])
    tone = sentiment_data.get("tone", "unknown")
    summary = sentiment_data.get("summary", "")
    highlights = sentiment_data.get("emotional_highlights", [])
    
    emoji = get_sentiment_emoji(overall)
    color = get_sentiment_color(score)
    
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, white, #f8f9fa); padding: 20px; border-radius: 12px; 
                border: 1px solid #e0e0e0; border-left: 5px solid {color}; margin: 10px 0;'>
        <div style='display: flex; align-items: center; gap: 15px; margin-bottom: 15px;'>
            <span style='font-size: 2.5em;'>{emoji}</span>
            <div>
                <h3 style='margin: 0; color: #333; background: none; -webkit-text-fill-color: #333;'>
                    {overall.title()} Sentiment
                </h3>
                <p style='margin: 5px 0 0 0; color: #666; font-size: 0.9em;'>
                    Score: {score:.2f} | Confidence: {confidence:.0%}
                </p>
            </div>
        </div>
        <p style='color: #444; margin: 0; line-height: 1.6;'>{summary}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🎭 Dominant Emotions:**")
        emotion_text = ", ".join([e.title() for e in emotions]) if emotions else "None detected"
        st.markdown(f"<p style='color: #333;'>{emotion_text}</p>", unsafe_allow_html=True)
    with col2:
        st.markdown("**🎙️ Tone:**")
        st.markdown(f"<p style='color: #333;'>{tone.title()}</p>", unsafe_allow_html=True)
    
    # Sentiment meter
    meter_pos = (score + 1) / 2 * 100
    st.markdown(f"""
    <div style='margin: 15px 0;'>
        <p style='color: #333; font-weight: 600; margin-bottom: 8px;'>Sentiment Meter:</p>
        <div style='background: linear-gradient(to right, #ef4444, #f59e0b, #6b7280, #84cc16, #10b981); 
                    height: 12px; border-radius: 6px; position: relative;'>
            <div style='position: absolute; left: {meter_pos}%; top: -4px; 
                        width: 20px; height: 20px; background: white; border: 3px solid {color}; 
                        border-radius: 50%; transform: translateX(-50%); box-shadow: 0 2px 6px rgba(0,0,0,0.2);'></div>
        </div>
        <div style='display: flex; justify-content: space-between; margin-top: 5px;'>
            <span style='color: #ef4444; font-size: 0.8em;'>Negative</span>
            <span style='color: #6b7280; font-size: 0.8em;'>Neutral</span>
            <span style='color: #10b981; font-size: 0.8em;'>Positive</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if highlights:
        with st.expander("🔍 Emotional Highlights"):
            for h in highlights:
                ic = {"high": "#ef4444", "medium": "#f59e0b", "low": "#6b7280"}.get(h.get("intensity", "low"), "#6b7280")
                st.markdown(f"""
                <div style='padding: 10px; margin: 5px 0; background: #f8f9fa; border-radius: 8px; border-left: 3px solid {ic};'>
                    <p style='color: #333; margin: 0; font-style: italic;'>"{h.get('text', '')}"</p>
                    <p style='color: #888; margin: 5px 0 0 0; font-size: 0.85em;'>{h.get('emotion', '').title()} - {h.get('intensity', '').title()} intensity</p>
                </div>
                """, unsafe_allow_html=True)
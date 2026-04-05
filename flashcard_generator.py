"""Flashcard Generator module for EchoMind"""
import json
import streamlit as st


def generate_flashcards(notes_content: str, groq_client, num_cards: int = 10,
                       model: str = "llama-3.3-70b-versatile") -> list:
    try:
        limited = notes_content[:6000]
        prompt = f"""Based on the following notes, generate exactly {num_cards} study flashcards.

Notes Content:
{limited}

Respond in JSON format:
{{
    "flashcards": [
        {{
            "id": 1,
            "front": "Question or term",
            "back": "Answer or definition",
            "category": "Topic category"
        }}
    ]
}}"""

        completion = groq_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert educator creating study flashcards."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )
        result = json.loads(completion.choices[0].message.content)
        return result.get("flashcards", [])
    except Exception as e:
        st.error(f"Flashcard generation failed: {str(e)}")
        return []


def render_flashcards(flashcards: list):
    """Render interactive flashcards"""
    if not flashcards:
        st.warning("No flashcards available.")
        return
    
    if 'current_card' not in st.session_state:
        st.session_state.current_card = 0
    if 'card_flipped' not in st.session_state:
        st.session_state.card_flipped = False
    
    total = len(flashcards)
    current = st.session_state.current_card
    
    # Safety check
    if current >= total:
        st.session_state.current_card = 0
        current = 0
    
    card = flashcards[current]
    
    st.progress((current + 1) / total, text=f"Card {current + 1} of {total}")
    
    category = card.get("category", "General")
    st.markdown(f"<span style='background: #4f46e5; color: white; padding: 4px 12px; border-radius: 12px; font-size: 0.85em;'>{category}</span>", unsafe_allow_html=True)
    
    if st.session_state.card_flipped:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #667eea, #764ba2); padding: 40px; margin: 15px 0; 
                    border-radius: 16px; text-align: center; min-height: 200px; display: flex; 
                    align-items: center; justify-content: center;
                    box-shadow: 0 8px 25px rgba(118, 75, 162, 0.3);'>
            <div>
                <p style='color: rgba(255,255,255,0.7); font-size: 0.9em; margin-bottom: 10px;'>ANSWER</p>
                <p style='color: white; font-size: 1.3em; line-height: 1.6; margin: 0;'>{card['back']}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style='background: white; padding: 40px; margin: 15px 0; border-radius: 16px; 
                    text-align: center; min-height: 200px; display: flex; align-items: center; 
                    justify-content: center; border: 2px solid #e0e0e0;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.08);'>
            <div>
                <p style='color: #888; font-size: 0.9em; margin-bottom: 10px;'>QUESTION</p>
                <p style='color: #333; font-size: 1.3em; line-height: 1.6; margin: 0; font-weight: 500;'>{card['front']}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("⬅️ Previous", use_container_width=True, disabled=(current == 0), key="fc_prev"):
            st.session_state.current_card = max(0, current - 1)
            st.session_state.card_flipped = False
            st.rerun()
    with c2:
        label = "🔄 Show Question" if st.session_state.card_flipped else "🔄 Show Answer"
        if st.button(label, use_container_width=True, key="fc_flip"):
            st.session_state.card_flipped = not st.session_state.card_flipped
            st.rerun()
    with c3:
        if st.button("➡️ Next", use_container_width=True, disabled=(current >= total - 1), key="fc_next"):
            st.session_state.current_card = min(total - 1, current + 1)
            st.session_state.card_flipped = False
            st.rerun()
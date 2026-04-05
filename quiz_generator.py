"""Quiz Generator module for EchoMind"""
import json
import streamlit as st


def generate_quiz(notes_content: str, groq_client, num_questions: int = 5, 
                  difficulty: str = "medium", model: str = "llama-3.3-70b-versatile") -> dict:
    try:
        limited = notes_content[:6000]
        prompt = f"""Based on the following notes, generate a quiz with exactly {num_questions} multiple-choice questions.
Difficulty level: {difficulty}

Notes Content:
{limited}

Respond in JSON format:
{{
    "quiz_title": "Title based on the content",
    "questions": [
        {{
            "id": 1,
            "question": "Question text here?",
            "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
            "correct_answer": "A",
            "explanation": "Brief explanation why this is correct"
        }}
    ]
}}

Make questions that test understanding, not just memorization."""

        completion = groq_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert educator. Generate clear, unambiguous multiple-choice questions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        return {"quiz_title": "Quiz Generation Failed", "questions": [], "error": str(e)}


def render_quiz(quiz_data: dict):
    """Render an interactive quiz in Streamlit"""
    if not quiz_data or not quiz_data.get("questions"):
        st.warning("No quiz questions available.")
        return
    
    st.markdown(f"#### 📝 {quiz_data.get('quiz_title', 'Quiz')}")
    questions = quiz_data["questions"]
    total = len(questions)
    
    if 'quiz_answers' not in st.session_state:
        st.session_state.quiz_answers = {}
    if 'quiz_submitted' not in st.session_state:
        st.session_state.quiz_submitted = False
    
    with st.form("quiz_form"):
        for i, q in enumerate(questions):
            qid = q.get("id", i + 1)
            st.markdown(f"""
            <div style='background: white; padding: 15px; margin: 10px 0; border-radius: 10px; 
                        border: 1px solid #ddd; border-left: 4px solid #4f46e5;'>
                <p style='color: #333; font-weight: 600; margin: 0;'>Q{qid}. {q['question']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            options = q.get("options", [])
            selected = st.radio(
                f"Select answer for Q{qid}:",
                options=options,
                key=f"quiz_q_{qid}",
                label_visibility="collapsed"
            )
            st.session_state.quiz_answers[qid] = selected
        
        submitted = st.form_submit_button("✅ Submit Quiz", use_container_width=True)
        if submitted:
            st.session_state.quiz_submitted = True
    
    if st.session_state.quiz_submitted:
        correct_count = 0
        st.markdown("---")
        st.markdown("#### 📊 Results")
        
        for q in questions:
            qid = q.get("id", 0)
            user_answer = st.session_state.quiz_answers.get(qid, "")
            correct = q.get("correct_answer", "")
            explanation = q.get("explanation", "")
            
            user_letter = user_answer[0] if user_answer else ""
            is_correct = user_letter.upper() == correct.upper()
            
            if is_correct:
                correct_count += 1
                icon = "✅"
                bc = "#10b981"
            else:
                icon = "❌"
                bc = "#ef4444"
            
            st.markdown(f"""
            <div style='background: white; padding: 15px; margin: 8px 0; border-radius: 8px; 
                        border-left: 4px solid {bc}; border: 1px solid #ddd;'>
                <p style='color: #333; margin: 0;'>{icon} <strong>Q{qid}:</strong> {q['question']}</p>
                <p style='color: #666; margin: 5px 0;'>Your answer: {user_answer}</p>
                <p style='color: {bc}; margin: 5px 0;'>Correct answer: {correct}</p>
                <p style='color: #888; font-style: italic; margin: 5px 0 0 0; font-size: 0.9em;'>💡 {explanation}</p>
            </div>
            """, unsafe_allow_html=True)
        
        pct = (correct_count / total * 100) if total > 0 else 0
        sc = "#10b981" if pct >= 70 else "#f59e0b" if pct >= 50 else "#ef4444"
        
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, white, #f0f0ff); padding: 25px; margin: 20px 0; 
                    border-radius: 12px; text-align: center; border: 2px solid {sc};'>
            <h2 style='color: {sc}; margin: 0; background: none; -webkit-text-fill-color: {sc};'>
                {correct_count}/{total} ({pct:.0f}%)
            </h2>
            <p style='color: #666; margin: 10px 0 0 0;'>
                {'Excellent! 🎉' if pct >= 80 else 'Good job! 👍' if pct >= 60 else 'Keep studying! 📚'}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔄 Retake Quiz"):
            st.session_state.quiz_answers = {}
            st.session_state.quiz_submitted = False
            st.rerun()
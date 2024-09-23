import streamlit as st
from youtube_summarizer import YouTubeSummarizer
from quiz_generator import QuizGenerator
from fpdf import FPDF

# CSS for reducing button size and other custom styling
def local_css():
    st.markdown("""
        <style>
        .sidebar .stButton button {
            padding: 0.2rem 0.5rem;
            font-size: 0.8rem;
        }
        .sidebar .stMarkdown h2 {
            font-size: 1rem;
            margin-bottom: 0.5rem;
        }
        .stButton>button {
            font-size: 1rem;
            padding: 0.3rem 0.6rem;
        }
        </style>
    """, unsafe_allow_html=True)

# Apply CSS to decrease button size
local_css()

def quiz_page(quiz_generator):
    """Displays the quiz page with a cleaner UI and real-time feedback."""
    st.title("🎓 YouTube Video Quiz")

    # Check if a summary exists
    summary = st.session_state.get('summary', None)
    if not summary and len(summary)<500:
        st.error("Not enough summary available to generate the quiz. Try different Video.")
        return

    # Generate questions if not already in session_state or fewer than 10 questions are generated
    if 'quiz_questions' not in st.session_state or len(st.session_state.quiz_questions) < 10:
        with st.spinner("Generating quiz, please wait..."):
            raw_quiz_text = quiz_generator.generate_quiz(summary)
            parsed_questions = quiz_generator.parse_quiz(raw_quiz_text) if raw_quiz_text else []

            # Check if there are at least 10 questions
            if len(parsed_questions) >= 10:
                st.session_state.quiz_questions = parsed_questions[:10]
                st.session_state.current_question_idx = 0
                st.session_state.selected_answers = [None] * len(st.session_state.quiz_questions)
            else:
                # If not enough questions, display an error message
                st.error("Not enough questions could be generated. Try again or select a different video with subtitles.")
                return

    questions = st.session_state.quiz_questions
    if not questions:
        st.error("No questions parsed from the quiz.")
        return

    # Track current question index
    current_idx = st.session_state.current_question_idx
    if current_idx < len(questions):
        current_question = questions[current_idx]

        # Sidebar for navigating questions
        with st.sidebar:
            st.subheader("📋 Navigate Questions")
            for idx in range(len(questions)):
                if st.button(f"Question {idx + 1}", key=f"nav_q_{idx}"):
                    st.session_state.current_question_idx = idx
                    st.rerun()

        # Main page layout for quiz content
        st.markdown(f"### Question {current_idx + 1}")
        question_text = current_question.get("question", "No question text found")
        st.write(f"**{question_text}**")

        # Ensure selected_answer is initialized to None if not already set
        selected_answer = st.session_state.selected_answers[current_idx]

        # Radio buttons for options, no index set if no selection has been made yet
        selected_option = st.radio(
            "Select your answer:",
            options=current_question["options"],
            index=current_question["options"].index(selected_answer) if selected_answer else None,  
            key=f"temp_option_{current_idx}",
        )

        # Save the selected answer in the session state when navigating
        col_prev, col_next = st.columns([1, 1])
        with col_prev:
            if current_idx > 0 and st.button("Previous"):
                st.session_state.selected_answers[current_idx] = selected_option
                st.session_state.current_question_idx -= 1
                st.rerun()

        with col_next:
            if current_idx < len(questions) - 1 and st.button("Next"):
                st.session_state.selected_answers[current_idx] = selected_option
                st.session_state.current_question_idx += 1
                st.rerun()

        # Submit button
        if current_idx == len(questions) - 1 and st.button("Submit Answers", key="submit_quiz"):
            st.session_state.selected_answers[current_idx] = selected_option
            grade_quiz(quiz_generator)



def grade_quiz(quiz_generator):
    st.title("Quiz Results 🎉")
    
    # Fetch the dynamically generated questions and correct answers
    questions = st.session_state.quiz_questions
    total_questions = len(questions)
    selected_answers = st.session_state.selected_answers
    
    correct_count = 0
    feedback_list = []

    for i in range(total_questions):
        user_answer = selected_answers[i]
        correct_answer = questions[i].get("correct_answer")
        question_text = f"Question {i+1}: {questions[i]['question']}"
        feedback_text = questions[i].get("feedback", "No feedback available")
        options = questions[i].get("options", [])
        
        # Initialize flags for correct answer and user-selected answer
        correct_answer_letter = None
        user_selected_letter = None
        
        # Check if correct_answer exists and extract the letter
        if correct_answer:
            correct_answer_letter = correct_answer[0]  # Extract the correct letter
        
        # Check if user_answer exists and extract the letter
        if user_answer:
            user_selected_letter = user_answer[1]  # Extract the selected letter from (A), (B), etc.

        # Create a formatted string for the options with checkmarks for correct and selected ones
        options_feedback = []
        for option in options:
            option_letter = option[1]  # Get the letter (A, B, C, etc.)
            option_text = option  # Complete option text (e.g., "(A) 5")
            
            if correct_answer_letter and option_letter == correct_answer_letter:
                options_feedback.append(f"{option_text} ✅")  # Mark the correct option
            elif user_selected_letter and option_letter == user_selected_letter:
                options_feedback.append(f"{option_text} ❌")  # Mark the user's selected wrong option
            else:
                options_feedback.append(option_text)  # No marks for unselected options
        
        # Determine if the user's answer was correct or incorrect
        if user_selected_letter and correct_answer_letter:
            if user_selected_letter == correct_answer_letter:
                correct_count += 1
                result = "Correct! ✅"
            else:
                result = f"Incorrect ❌. The correct answer is {correct_answer}"
        else:
            result = "No answer selected or incorrect answer parsing"

        # Append the feedback for each question
        feedback_list.append({
            "question": question_text,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "result": result,
            "options_feedback": "<br>".join(options_feedback),  # Joining all options with <br> for vertical order
            "feedback": feedback_text  # Always include feedback now
        })

    # Calculate score and display it
    score = correct_count / total_questions * 100
    st.markdown(f"### You got {correct_count} out of {total_questions} questions correct.")
    st.markdown(f"### Your score: {score:.2f}%")
    
    # Display feedback in a structured format for each question
    for i, fb in enumerate(feedback_list):
        st.markdown(f"**{fb['question']}**")
        st.markdown(f"Your answer: {fb['user_answer'] if fb['user_answer'] else 'No answer'}")
        st.markdown(f"Result: {fb['result']}")
        st.markdown(f"**Options:**<br>{fb['options_feedback']}", unsafe_allow_html=True)  # Display options in vertical order
        if fb['feedback']:
            st.markdown(f"**Feedback:** {fb['feedback']}")
        st.markdown("---")
    
    # Optionally generate and download the feedback in a PDF
    pdf_filename = generate_pdf(feedback_list, correct_count, total_questions, score)

    with open(pdf_filename, "rb") as pdf_file:
        st.download_button(
            label="📄 Download Results as PDF",
            data=pdf_file,
            file_name=pdf_filename,
            mime="application/pdf"
        )


def generate_pdf(feedback_list, correct_count, total_questions, score):
    """Generate a PDF from the feedback and save it to a file."""

    # Initialize PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Quiz Results", ln=True, align='C')

    # Score
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt=f"Total Correct: {correct_count} out of {total_questions}", ln=True)
    pdf.cell(200, 10, txt=f"Score: {score:.2f}%", ln=True)

    # Add feedback for each question
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    for fb in feedback_list:
        # Handle the correct/incorrect markers with text-based symbols
        result_text = fb['result'].replace('✅', '[~]').replace('❌', '')
        feedback_text = fb['feedback'].replace('✅', '[~]').replace('❌', '')

        # Adding feedback to the PDF, including options
        pdf.multi_cell(0, 10, f"{fb['question']}\nYour answer: {fb['user_answer'] if fb['user_answer'] else 'No answer'}\nResult: {result_text}")
        
        # Adding the options and marking correct/incorrect
        options_text = fb['options_feedback'].replace('<br>', '\n').replace('✅', '[~]').replace('❌', '')
        pdf.multi_cell(0, 10, f"Options:\n{options_text}")

        # Adding feedback
        pdf.multi_cell(0, 10, f"Feedback: {feedback_text}\n")
        pdf.ln(5)  # Add some space between questions

    # Save PDF locally
    pdf_filename = "quiz_results.pdf"
    pdf.output(pdf_filename)

    return pdf_filename



def summary_page(summarizer):
    """Displays the YouTube summary page."""
    st.title("🎥 YouTube Video Summarizer")
    
    # Check if the summary is already present to avoid rerunning the summary logic
    if 'summary' not in st.session_state:
        youtube_url = st.text_input("Enter YouTube Video URL", key="youtube_url")

        if youtube_url:
            # Only display spinner for summary generation
            with st.spinner("Generating summary, please wait..."):
                summary = summarizer.generate_summary(youtube_url)

            if summary:
                st.session_state.summary = summary  # Save summary to session state
                st.subheader("📑 Video Summary:")
                st.write(summary)

                if summary.strip():
                    st.download_button(
                        label="Download Summary",
                        data=summary,
                        file_name='youtube_summary.txt',
                        mime='text/plain'
                    )

                if st.button("Ready for Quiz"):
                    st.session_state.page = 'quiz_page'
                    st.rerun()  # Move to quiz page after quiz generation
    else:
        # If the summary is already generated, display it and the button to move to quiz page
        st.subheader("📑 Video Summary:")
        st.write(st.session_state.summary)

        if st.button("Ready for Quiz"):
            st.session_state.page = 'quiz_page'
            st.rerun()  # Move to quiz page after quiz generation

def main():
    summarizer = YouTubeSummarizer()
    quiz_generator = QuizGenerator()

    if 'page' not in st.session_state:
        st.session_state.page = 'summary_page'

    if st.session_state.page == 'summary_page':
        summary_page(summarizer)
    elif st.session_state.page == 'quiz_page':
        quiz_page(quiz_generator)


if __name__ == "__main__":
    main()

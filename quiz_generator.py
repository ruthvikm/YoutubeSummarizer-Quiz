import re
import google.generativeai as genai
import streamlit as st

class QuizGenerator:
    def __init__(self):
        self.model = self.initialize_model()

    def initialize_model(self, model_name="gemini-1.5-flash-001"):
        """Initialize the Gemini model."""
        try:
            model = genai.GenerativeModel(model_name)
            return model
        except Exception as e:
            st.error(f"Error initializing the model: {e}")
            return None

    def generate_quiz(self, summary, num_questions=10):
        """Generate quiz questions based on the summary."""
        try:
            quiz_prompt = f"""
            Based on the following summary, generate {num_questions} multiple-choice questions with 4 options each.
            The questions should be relevant to the context of the video, and the type of questions should be generated according to the nature of the content:
            
            1. **For math-related content**:
                - Include mathematical expressions, equations, or problem-solving steps in both the questions and options.
                - **Solve each math question step by step**, and use the **evaluated result** as the correct answer.
                - Verify that the correct answer is included in the options.
                - Provide realistic distractors (wrong options) that reflect common mistakes.
                - The correct answer **must be included** as one of the four options, and **verified by evaluating the equation**.
                - **Explaination must include all the steps to solve the problem**.

            2. **For conceptual or non-math content**:
                - Create fact-based or conceptual questions that assess the learner's understanding of the content.
                - Ensure the questions are contextually accurate and reflect the key concepts or points from the summary.
                - Provide a detailed explanation for the correct answer, highlighting why it is correct and why other options are incorrect.

            3. Evaluate all the questions and provide the correct answer in the options.
            4. If any question was not evaluated or without explaination exists, skip the question.

            **Formatting**:
            For each question, use the following structure:

            'Question X: [Question text or mathematical expression]'
            'Options:'
            (A) [Option A: text or mathematical expression]
            (B) [Option B: text or mathematical expression]
            (C) [Option C: text or mathematical expression]
            (D) [Option D: text or mathematical expression]

            'Correct Answer: [Option letter & option text]'
            'Explanation: [How to solve a problem or why the correct answer is the best option]

            Here is the summary of the video content to base the questions on:
            {summary}
            """

            response = self.model.generate_content(quiz_prompt)
            generated_quiz_text = response.text

            # Verify the math problems
            verified_quiz = self.verify_math_answers(generated_quiz_text)

            return verified_quiz
        except Exception as e:
            st.error(f"Error generating the quiz: {e}")
            return None

    def verify_math_answers(self, quiz_text):
        """
        This function verifies that the correct answer for math problems is correctly calculated
        and included in the multiple-choice options.
        """
        questions = self.parse_quiz(quiz_text)
        
        for question in questions:
            if "solve" in question["question"].lower():  # Only check for math-related questions
                # Extract the equation from the question
                try:
                    equation = self.extract_equation_from_question(question["question"])
                    correct_answer = self.solve_equation(equation)
                    
                    # Check if the correct answer is in the options
                    if not any(correct_answer in option for option in question["options"]):
                        st.warning(f"Correct answer {correct_answer} was not found in options. Adjusting the options.")
                        # Replace one of the incorrect options with the correct answer
                        question["options"][-1] = f"(D) x = {correct_answer}"  # Replace last option for now

                except Exception as e:
                    pass

        # Reformat the quiz back into a text structure (optional)
        return self.format_quiz(questions)

    def extract_equation_from_question(self, question_text):
        """Extract the equation from the question text."""
        # Extracts the mathematical expression from the question
        match = re.search(r'(\d+x.*=\d+)', question_text)
        if match:
            return match.group(1)
        else:
            raise ValueError("No valid equation found in the question.")

    def solve_equation(self, equation):
        """Solve a simple linear equation."""
        # Parse the equation and solve for x
        import sympy as sp
        x = sp.symbols('x')
        solution = sp.solve(equation, x)
        return solution[0] if solution else None

    def format_quiz(self, questions):
        """Format the list of questions into a readable text format (optional)."""
        formatted_quiz = ""
        for i, question in enumerate(questions):
            formatted_quiz += f"Question {i + 1}: {question['question']}\n"
            for option in question['options']:
                formatted_quiz += f"{option}\n"
            formatted_quiz += f"Correct Answer: {question['correct_answer']}\n"
            formatted_quiz += f"Explanation: {question['feedback']}\n\n"
        return formatted_quiz

    def clean_text(self, text):
        """Clean and format text by removing unwanted characters."""
        return re.sub(r'\*\*|\:\n|\n+', '', text).strip()

    def parse_quiz(self, quiz_text):
        """Parse quiz text into a list of questions, options, correct answers, and feedback."""
        questions = []
        lines = quiz_text.strip().split("\n")
        current_question = None

        # Regex to capture the question, options, correct answer, and explanation
        question_regex = re.compile(r'Question \d+:\s*(.*)', re.IGNORECASE)
        option_regex = re.compile(r'\(([A-Da-d])\)\s*(.*)')
        correct_answer_regex = re.compile(r'Correct Answer:\s*\(?([A-Da-d])\)?')
        explanation_regex = re.compile(r'Explanation:\s*(.*)')

        question_lines = []  # Collect lines for a multi-line question

        for line in lines:
            cleaned_line = self.clean_text(line)

            # Match a new question
            question_match = question_regex.match(cleaned_line)
            if question_match:
                # If there's an existing question, append it
                if current_question and current_question["options"]:
                    questions.append(current_question)

                # Start a new question
                current_question = {"question": "", "options": [], "correct_answer": None, "feedback": ""}
                question_lines = [question_match.group(1).strip()]

            # Continue collecting lines for the current question until options start
            elif current_question and cleaned_line and not option_regex.match(cleaned_line) and not correct_answer_regex.match(cleaned_line) and not explanation_regex.match(cleaned_line):
                question_lines.append(cleaned_line)

            # Match the options
            elif option_regex.match(cleaned_line) and current_question:
                current_question["question"] = " ".join(question_lines).replace("Options:", "").strip()  # Remove any trailing "Options" word
                option_match = option_regex.match(cleaned_line)
                if option_match:
                    current_question["options"].append(f"({option_match.group(1)}) {option_match.group(2)}")

            # Match the correct answer
            correct_answer_match = correct_answer_regex.match(cleaned_line)
            if correct_answer_match and current_question:
                current_question["correct_answer"] = correct_answer_match.group(1).strip()

            # Match the explanation
            explanation_match = explanation_regex.match(cleaned_line)
            if explanation_match and current_question:
                current_question["feedback"] = explanation_match.group(1).strip()

        # Append the last question if not already appended
        if current_question and current_question["options"]:
            questions.append(current_question)

        # Post-process questions (ensure 4 options, explanation present)
        for question in questions:
            # Ensure there are 4 options by appending placeholders if necessary
            if len(question["options"]) < 4:
                while len(question["options"]) < 4:
                    question["options"].append("(N/A) Option not provided")

            # Ensure every question has feedback
            if not question["feedback"]:
                question["feedback"] = "No explanation provided."

        return questions

import re
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import streamlit as st
import os
import google.generativeai as genai
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables from the .env file
load_dotenv()

# Get the API key from the environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Check if the API key exists and configure the Gemini API
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    st.error("Gemini API key is missing. Please set the GEMINI_API_KEY in your environment variables.")


class YouTubeSummarizer:
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

    def get_video_id(self, url):
        """Extract the video ID from the YouTube URL."""
        video_id = url.split("v=")[1]
        if "&" in video_id:
            video_id = video_id.split("&")[0]

        return video_id

    def get_video_transcripts(self, video_id):
        """Fetch the transcript of a YouTube video."""
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcription = " ".join([transcript['text'] for transcript in transcript_list])
            return transcription
        except Exception as e:
            st.error(f"Error fetching transcript: {e}")
            return None

    def chunk_text(self, text, max_length):
        """Split the text into chunks of a specified length."""
        words = text.split()
        chunks = []
        for i in range(0, len(words), max_length):
            chunk = " ".join(words[i:i + max_length])
            chunks.append(chunk)
        return chunks

    def get_chunked_summary(self, transcription):
        """Summarize the transcription in chunks using the model, emphasizing equations, key points, and clear steps."""
        max_chunk_size = 500
        transcription_chunks = self.chunk_text(transcription, max_chunk_size)
        final_summary = ""

        # Enhanced prompt to distinguish between math and conceptual videos
        for chunk in transcription_chunks:
            prompt = f"""
            Based on the content in the following transcript, summarize appropriately, keeping in mind the type of content:
            
            1. **For conceptual content**:
            - Clearly explain the key concepts and ideas.
            - Emphasize important points, definitions, and their relationships.
            - Ensure the summary is structured logically and easy to follow for someone new to the topic.

            2. **For mathematical content**:
            - Include all the relevant equations and steps used to solve problems.
            - For each equation, break down the steps and explain the logic behind them.
            - Provide a clear explanation of how to approach similar problems, focusing on why specific operations are used.
            - Highlight any formulas or rules that are critical to understanding the solution.
            
            3. Make the content realistic with a proper flow and summary.

            Transcript:
            \n\n{chunk}
            """
            chunk_summary = self.get_response(self.model, prompt)
            final_summary += chunk_summary + "\n\n"

        return final_summary




    def get_response(self, model, prompt):
        """Generate response from the model with safety and empty response checks."""
        try:
            response = model.generate_content(prompt)
            
            # Check if there are any valid responses
            if not response or not hasattr(response, 'text') or not response.text:
                st.error("No valid response generated. The content may have been blocked by the safety filter.")
                
                # Check safety ratings if available
                if hasattr(response, 'candidate') and hasattr(response.candidate, 'safety_ratings'):
                    safety_info = response.candidate.safety_ratings
                    st.warning(f"Response was blocked due to safety ratings: {safety_info}")
                return ""
            
            # Return the response text if valid
            return response.text
        except Exception as e:
            st.error(f"Error generating response: {e}")
            return ""


    def generate_summary(self, url):
        """Fetch transcription and generate summary for the YouTube video."""
        video_id = self.get_video_id(url)
        transcription = self.get_video_transcripts(video_id)
        if transcription:
            summary = self.get_chunked_summary(transcription)
            return summary
        else:
            return None


# Function to display the UI and download button
def summary_page(summarizer):
    """Displays the YouTube summary page."""
    st.title("YouTube Video Summarizer")
    youtube_url = st.text_input("Enter YouTube Video URL", key="youtube_url")

    if youtube_url:
        summary = summarizer.generate_summary(youtube_url)
        if summary:
            st.subheader("Video Summary:")
            st.write(summary)

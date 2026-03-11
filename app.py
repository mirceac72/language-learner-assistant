# Language Learner Assistant

import nltk
import streamlit as st

# Download required NLTK data
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")

try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab")

try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords")


from src.language_learner.core.application import LanguageLearnerApplication
from src.language_learner.core.llm_client import MistralLLMClient
from src.language_learner.core.mock_llm import MockLLMClient
from src.language_learner.ui.exercise_display import (
    display_exercise,
    display_exercise_completion,
)
from src.language_learner.ui.vocabulary_display import display_vocabulary
from src.language_learner.web.vocabulary_extractor import VocabularyExtractor


def main():
    st.title("French Language Learner Assistant")
    st.write("Enter a French web page URL to extract vocabulary and create exercises:")

    # Initialize application with real Mistral LLM
    if "app" not in st.session_state:
        try:
            # Try to use real Mistral LLM client
            llm_client = MistralLLMClient()
            st.session_state.app = LanguageLearnerApplication(llm_client)
            st.session_state.llm_configured = True
        except ValueError as e:
            if "Mistral API key not provided" in str(e):
                st.warning(
                    "Mistral LLM not configured. Using mock LLM for exercise generation."
                )
                # Fall back to mock LLM
                llm_client = MockLLMClient()
                st.session_state.app = LanguageLearnerApplication(llm_client)
                st.session_state.llm_configured = False
            else:
                st.error(f"Failed to initialize Mistral LLM: {e}")
                st.session_state.llm_configured = False
        except Exception as e:
            st.error(f"Failed to initialize Mistral LLM: {e}")
            st.session_state.llm_configured = False
        st.session_state.exercises = []
        st.session_state.current_exercise = None
        st.session_state.show_exercises = False

    url = st.text_input("URL:", "")

    if st.button("Extract Vocabulary and Create Exercises"):
        if url:
            if not st.session_state.get("llm_configured", False):
                st.error("Cannot generate exercises: Mistral LLM not configured.")
                return

            with st.spinner("Fetching and processing content..."):
                extractor = VocabularyExtractor()

                # Fetch and process the web page
                html = extractor.fetch_web_page(url)
                if html:
                    text = extractor.extract_text_from_html(html)
                    vocabulary = extractor.extract_vocabulary(text)

                    st.success("Vocabulary extracted successfully!")

                    # Display vocabulary
                    vocabulary_words = display_vocabulary(vocabulary)

                    # Generate exercises
                    with st.spinner("Generating exercises..."):
                        exercises = st.session_state.app.create_exercises(
                            vocabulary_words
                        )
                        st.session_state.exercises = exercises
                        st.session_state.show_exercises = True
                        st.success(f"Generated {len(exercises)} exercises!")
        else:
            st.warning("Please enter a URL")

    # Show exercises if available
    if st.session_state.show_exercises and st.session_state.exercises:
        st.subheader("Exercises")

        if "player" not in st.session_state or st.session_state.player is None:
            st.session_state.player = st.session_state.app.start_exercise_session(
                st.session_state.exercises
            )

        player = st.session_state.player
        current_exercise = player.get_current_exercise()

        if current_exercise:
            exercise_completed = display_exercise(
                current_exercise, player, st.session_state.app
            )
            if exercise_completed:
                st.rerun()
        else:
            display_exercise_completion()


if __name__ == "__main__":
    main()

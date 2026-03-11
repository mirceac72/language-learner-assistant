"""Vocabulary Display Module

This module provides functionality to display extracted vocabulary words.
"""

from collections.abc import Sequence

import streamlit as st


def display_vocabulary(
    vocabulary: Sequence[tuple[str, int]], top_n: int = 10
) -> list[str]:
    """Display the top vocabulary words extracted from text.

    Args:
        vocabulary: Sequence of (word, count) tuples
        top_n: Number of top words to display

    Returns:
        List of vocabulary words displayed
    """
    st.subheader("Top Vocabulary Words")
    vocabulary_words = [word for word, count in vocabulary[:top_n]]
    for word, count in vocabulary[:top_n]:
        st.write(f"{word}: {count}")

    return vocabulary_words

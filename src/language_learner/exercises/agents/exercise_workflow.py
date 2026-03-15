# Exercise Workflow using LangGraph
import logging
from typing import TypedDict

from langgraph.graph import END, StateGraph

from src.language_learner.core.llm_interface import LLMClient
from src.language_learner.exercises.agents.exercise_creator import (
    ExerciseCreatorAgent,
)
from src.language_learner.exercises.agents.exercise_reviewer import (
    ExerciseReviewerAgent,
)
from src.language_learner.models.exercise import Exercise

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ExerciseWorkflowState(TypedDict):
    """State for the complete exercise workflow"""
    vocabulary_words: list[str]
    generated_exercises: list[Exercise]
    reviewed_exercises: list[Exercise]
    rejected_exercises: list[dict]
    feedback: list[str]
    iteration: int


class ExerciseWorkflow:
    """Orchestrates the exercise creation and review workflow using LangGraph"""

    def __init__(self, llm_client: LLMClient) -> None:
        """Initialize exercise workflow.

        Args:
            llm_client: LLM client for exercise generation and review
        """
        self.llm_client = llm_client
        self.creator_agent = ExerciseCreatorAgent(llm_client)
        self.reviewer_agent = ExerciseReviewerAgent(llm_client)

    def create_workflow(self):
        """Create the LangGraph workflow.

        Returns:
            Configured LangGraph workflow
        """
        workflow = StateGraph(ExerciseWorkflowState)

        # Add creator node
        creator_node = self.creator_agent.create_node()
        workflow.add_node("creator", creator_node)

        # Add reviewer node
        reviewer_node = self.reviewer_agent.create_node()
        workflow.add_node("reviewer", reviewer_node)

        # Define workflow edges
        workflow.add_edge("creator", "reviewer")
        workflow.add_edge("reviewer", END)

        # Set entry point
        workflow.set_entry_point("creator")

        return workflow

    def run_workflow(self, vocabulary_words: list[str], max_iterations: int = 2) -> list[Exercise]:
        """Run the complete workflow with multiple iterations.

        Args:
            vocabulary_words: List of vocabulary words to create exercises for
            max_iterations: Maximum number of iterations (creator → reviewer cycles)

        Returns:
            List of approved exercises
        """
        workflow = self.create_workflow()
        compiled_workflow = workflow.compile()

        # Initialize state
        state: ExerciseWorkflowState = {
            "vocabulary_words": vocabulary_words,
            "generated_exercises": [],
            "reviewed_exercises": [],
            "rejected_exercises": [],
            "feedback": [],
            "iteration": 1,
        }

        # Run multiple iterations
        for iteration in range(1, max_iterations + 1):
            logger.info(f"Running iteration {iteration}/{max_iterations}")

            # Update iteration in state
            state["iteration"] = iteration

            # Run workflow
            result = compiled_workflow.invoke(state)

            # Update state with results
            state["generated_exercises"] = result.get("generated_exercises", [])
            state["reviewed_exercises"] = result.get("reviewed_exercises", [])
            state["rejected_exercises"] = result.get("rejected_exercises", [])
            state["feedback"] = result.get("feedback", [])

            # If we have good exercises and this isn't the last iteration,
            # use feedback to improve in next iteration
            if iteration < max_iterations and state["feedback"]:
                logger.info(f"Iteration {iteration} completed: {len(state['reviewed_exercises'])} approved, {len(state['rejected_exercises'])} rejected")

                # Prepare for next iteration - keep rejected exercises for improvement
                # but focus on new generation for remaining words
                if iteration == 1:
                    # In second iteration, try to improve rejected exercises
                    state["vocabulary_words"] = [
                        word for word in vocabulary_words[:5]  # Limit to top 5 for second iteration
                    ]
            else:
                break

        logger.info(f"Workflow completed: {len(state['reviewed_exercises'])} final exercises approved")

        return state["reviewed_exercises"]

    def run_simple_workflow(self, vocabulary_words: list[str]) -> list[Exercise]:
        """Run a simplified single-iteration workflow.

        Args:
            vocabulary_words: List of vocabulary words

        Returns:
            List of approved exercises
        """
        return self.run_workflow(vocabulary_words, max_iterations=1)

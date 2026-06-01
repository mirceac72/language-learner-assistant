# Language Learner Assistant - Setup Instructions

## Prerequisites

- Python 3.12+
- Streamlit
- Mistral AI API key

## Installation


## Running the Application

1. **Start the Streamlit app:**
   ```bash
   set -a && source .env && set +a && streamlit run app.py
   ```

2. **Access the application:**
   - Open your browser to `http://localhost:8501`
   - Enter a French website URL
   - Click "Extract Vocabulary and Create Exercises"

## Development

### Running Tests
```bash
uv run -m pytest tests/ -v
```

### Running Ruff (Linter)
```bash
uv run ruff check .
```

### Formatting Code with Ruff
```bash
uv run ruff format .
```

### Auto-fixing Issues with Ruff
```bash
uv run ruff check --fix .
```

### Using Mock LLM for Development
Tests use `MockLLMClient` to avoid API calls. For development without an API key:

1. Temporarily modify `app.py` to use `MockLLMClient`
2. Run with: `streamlit run app.py`
3. Note: Mock mode generates predictable exercises for testing only

### Running Quality Analysis Notebook
For Step 1 of the Implementation Plan (Establish Quality Baseline):

1. **Open the notebook:**
   ```bash
   jupyter notebook experiments/baseline_quality_analysis.ipynb
   ```

2. **Or execute directly from command line:**
   ```bash
   cd /workspaces/language-learner-assistant
   source .env
   PYTHONPATH=/workspaces/language-learner-assistant \
     jupyter nbconvert --to notebook --execute \
     experiments/baseline_quality_analysis.ipynb \
     --inplace
   ```

## Configuration

The application uses the following environment variables:

- `MISTRAL_API_KEY` - Required for Mistral LLM access
- `MISTRAL_MODEL` - Optional, defaults to "mistral-small"

## Security

- Never commit your API key to version control
- Use environment variables or secret management systems
- Rotate your API key regularly
- Keep dependencies updated
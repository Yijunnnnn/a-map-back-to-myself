# A Map Back to Myself (a-map-back-to-myself)

A Map Back to Myself is a warm, evidence-based CBT companion application designed to help users reframe self-doubt by checking automatic thoughts against concrete personal history and achievements.

## Features
- **Warm CBT Reframes**: Analyzes automatic thoughts and cognitive distortions to suggest balanced, evidence-based alternative thoughts.
- **Privacy First**: Fully isolated local environments, ensuring that raw journals and documents are kept secure on your local device.
- **Evidence Card Mapping**: Generates structured, clickable evidence cards with standalone citations.
- **Notion-Style Browse Database**: Manage and browse your memory logs and imported files inside an easy-to-use table grid.

## How to Run the Demo Locally

This project uses `uv` for package management and script execution.

### 1. Prerequisites
Ensure you have Python 3.10+ and `uv` installed. If you don't have `uv` installed, you can install it using:
```bash
pip install uv
```

### 2. Setup the Environment
Copy the example environment file:
```bash
cp .env.example .env
```
Open `.env` and configure your API keys (e.g. `GEMINI_API_KEY`) if running in real LLM mode. By default, the system will use Mock Mode if no API key is specified.

### 3. Install Dependencies
Run the package installation:
```bash
uv pip install -e .
```

### 4. Rebuild the Database
To initialize the demo database and rebuild the retrieval indexes, run:
```bash
uv run python -m app.cli rebuild
```

### 5. Launch the Streamlit App
Run the local Streamlit application:
```bash
uv run streamlit run app/ui.py
```
Open your browser and navigate to `http://localhost:8501`.

## Development & Evaluation
To run the local BDD safety and evaluation test suite:
```bash
uv run python -m eval.eval_runner
```


# Personal News Intelligence Agent

A personal agent that fetches RSS feeds, summarizes and tags them using an LLM, and allows natural language querying.

## Setup

1.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configuration**:
    - Copy `.env.example` to `.env` and add your OpenAI API key.
    - Edit `config.yaml` to add/remove RSS feeds and adjust tagging criteria.

3.  **Run**:
    - **Ingest (Fetch & Analyze)**:
      ```bash
      python main.py ingest
      ```
    - **Query**:
      ```bash
      python main.py query "What are the latest funding opportunities in Fintech?"
      ```

## Project Structure

- `src/fetcher.py`: Handles RSS feed fetching.
- `src/analyzer.py`: Uses LLM to summarize and tag articles.
- `src/storage.py`: Manages SQLite database.
- `src/interface.py`: Handles user queries.
- `config.yaml`: Configuration for feeds and agent behavior.

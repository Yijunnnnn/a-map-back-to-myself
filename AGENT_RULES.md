# Agent Rules - SelfMap Agent

These rules govern the development and runtime behavior of the SelfMap Agent.

## 1. Interaction Rules
- **No Diagnostics**: Never use clinical terms like "Major Depressive Disorder", "GAD", "OCD", or "PTSD" in response to user inputs. Use general descriptive terms like "cognitive pattern" or "unhelpful thought pattern".
- **Validate and Challenge**: Always validate the user's emotions (e.g., "It's understandable to feel frustrated") before analyzing the thoughts for distortions (e.g., "However, thinking this always happens might be an overgeneralization").
- **PII Scrubbing**: Never process unredacted user journals using external LLM APIs.

## 2. Technical Code Guidelines
- **Type Hints**: All Python functions must include clear type hints.
- **Error Handling**: Catch API issues gracefully and fallback to local heuristics.
- **Append-only Logs**: Write event logs in standard JSONL (JSON Lines) format to avoid file lock issues.

# Daily Ninja Code
Latest idea (UTC): 2025-11-19 — ninja date cipher: 2025-11-19
Context: weather=rain; holidays=Garifuna Settlement Day, Repentance and Prayer Day, National Day, Discovery of Puerto Rico; topics=none

This repository generates and submits a daily Python "ninja" learning script via a scheduled workflow.

## Overview

- Deterministic idea chosen from the UTC date
- Ideas are refreshed daily via Hugging Face using date, weather, global holidays, and trending topics
- Code generated via Hugging Face Inference when `HF_TOKEN` is set
- Falls back to a compact standard‑library script otherwise
- Output saved under `generated/YYYY/MM/`
- A Pull Request is opened and merged automatically

## Requirements

- Python 3.11+
- Optional: Hugging Face Inference API token

## Configuration

- `HF_MODEL`: model id (default `bigcode/starcoder2-3b`)
- `HF_TOKEN`: Hugging Face token for API access
- `LOCATION_LAT` / `LOCATION_LON`: optional coordinates for weather context (default: London)
- `WIKI_LANG`: language code for Wikipedia trending topics (default: `en`)
- Model fallback: if the selected model is unavailable, falls back to `bigcode/starcoder2-1b` and then `HuggingFaceH4/zephyr-7b-beta`.
- `OLLAMA_MODEL` (optional): use a local model via Ollama at `http://localhost:11434`. Example: `OLLAMA_MODEL=starcoder2:1b`.
- `.env` (optional): local overrides for the above keys. Example:

```
HF_TOKEN=your_hf_token
HF_MODEL=bigcode/starcoder2-3b
LOCATION_LAT=51.5074
LOCATION_LON=-0.1278
WIKI_LANG=en
```

## Local Usage

```bash
python main.py
```

Tip: For local testing, you can set a smaller free model in `.env`:

```
HF_MODEL=bigcode/starcoder2-1b
```

Or install Ollama and run locally:

```
brew install ollama    # macOS
winget install Ollama  # Windows
ollama pull starcoder2:1b
```

Then set:

```
OLLAMA_MODEL=starcoder2:1b
```

Generates a file like `generated/2025/11/2025-11-19_prime-constellation-explorer.py` and prints metadata.

## CI Workflow

- Scheduled daily at 00:00 UTC
- Uses `actions/setup-python@v5` and runs `python main.py` (refreshes the latest idea via AI and generates the script)
- Creates and merges a PR with the generated script

## Folder Structure

- `main.py`: generator script
- `generated/`: daily outputs organized by year and month
- `.github/workflows/daily-ninja.yml`: CI scheduler and PR automation

## License

MIT License. See `LICENSE`.

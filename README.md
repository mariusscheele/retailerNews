# Retailer News API

## Prerequisites

Create and activate a Python virtual environment, then install the project dependencies:

```bash
python -m venv .venv
# On Windows
.venv\\Scripts\\activate
# On Unix or macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## Running the server

Launch the FastAPI server with Uvicorn using the module form so it also works when the `uvicorn` executable is not on your PATH:

```bash
python -m uvicorn main:app --reload
```

If you need to listen on a different port, add the `--port` flag (for example `--port 3000`).

The application will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000) by default.
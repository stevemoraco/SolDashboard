#!/usr/bin/env python3
"""FastAPI server for Sol Dashboard with data collection and analytics."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=5000, reload=False)

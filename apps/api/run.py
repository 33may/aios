#!/usr/bin/env python3
"""
Run the Knowledge Graph API server.

Usage:
    cd /home/may33/projects/aios
    python -m apps.api.run

Or with uvicorn directly:
    cd /home/may33/projects/aios
    uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
"""

import uvicorn
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if __name__ == "__main__":
    uvicorn.run(
        "apps.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

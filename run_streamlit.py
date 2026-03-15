#!/usr/bin/env python3
"""Wrapper script to run Streamlit with proper logging configuration."""

import logging
import os
import subprocess
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure logging to show in terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr,
    force=True
)

# Use the specified Streamlit app or default to app.py
if len(sys.argv) > 1:
    streamlit_app = sys.argv[1]
else:
    streamlit_app = 'app.py'
    if not os.path.exists(os.path.join(project_root, streamlit_app)):
        print("Error: app.py not found. Please specify the correct Streamlit app path.")
        print("Usage: python run_streamlit.py your_streamlit_app.py")
        sys.exit(1)

print(f"Starting Streamlit app: {streamlit_app}")
print("Logs will appear below. Press Ctrl+C to stop.")
print("=" * 60)

# Run streamlit
try:
    subprocess.run([sys.executable, "-m", "streamlit", "run", streamlit_app], check=True)
except subprocess.CalledProcessError as e:
    print(f"Streamlit exited with error: {e}")
    sys.exit(e.returncode)
except KeyboardInterrupt:
    print("\nStreamlit stopped by user.")
    sys.exit(0)

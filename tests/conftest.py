import os
import sys
from dotenv import load_dotenv

# Set required environment variables for testing
# These must be set before importing any module that instantiates Settings
# Load .env.test
load_dotenv(os.path.join(os.path.dirname(__file__), ".env.test"), override=True)

# Ensure project root is in pythonpath
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

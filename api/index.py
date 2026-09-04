import os
import sys

# Ensure project root and arthraksha module are on sys.path for Vercel Serverless
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_CURRENT_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

_ARTHRAKSHA_DIR = os.path.join(_PROJECT_ROOT, "arthraksha")
if _ARTHRAKSHA_DIR not in sys.path:
    sys.path.insert(0, _ARTHRAKSHA_DIR)

# Import the main FastAPI application instance
from arthraksha.api.main import app

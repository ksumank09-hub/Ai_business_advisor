"""
api/index.py
------------
Serverless entry point for Vercel deployment.
Exposes the WSGI Flask application instance as `app`.
"""

import os
import sys

# Add project root directory to sys.path so all internal modules resolve correctly
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app

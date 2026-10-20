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

from app import app as flask_app


class VercelPathMiddleware:
    """
    Ensures Vercel rewritten paths (e.g. /api/index, /api/index.py)
    map properly to Flask's root and internal routes.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        # If Vercel rewrites and passes the destination path instead of original:
        if path in ("/api/index", "/api/index.py", "/api", "/api/"):
            environ["PATH_INFO"] = "/"
        elif path.startswith("/api/index/"):
            environ["PATH_INFO"] = path[len("/api/index"):]
        elif path.startswith("/api/index.py/"):
            environ["PATH_INFO"] = path[len("/api/index.py"):]

        return self.wsgi_app(environ, start_response)


# Wrap Flask app with the middleware
app = VercelPathMiddleware(flask_app)

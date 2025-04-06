import os
import sys

# Add the parent directory to the path so we can import app.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our Chainlit app
import app

# This is necessary for Vercel serverless functions
# It exports the Chainlit ASGI app
from chainlit.server import app as chainlit_app
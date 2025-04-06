import os
import sys
from pathlib import Path

# Add the root directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import chainlit as cl
from chainlit.server import app

# Import our app file (which will register Chainlit handlers)
import app as resume_app

# Export the ASGI app explicitly
# This is the key line that Vercel needs
handler = app
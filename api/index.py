from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Resume Analyzer - Redirect</title>
            <meta http-equiv="refresh" content="0;url=https://chainlit-resume-analyzer.onrender.com">
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 40px; }
                h1 { color: #2563eb; }
            </style>
        </head>
        <body>
            <h1>Resume Analyzer</h1>
            <p>Redirecting you to the application...</p>
            <p>If you are not redirected, <a href="https://chainlit-resume-analyzer.onrender.com">click here</a>.</p>
        </body>
        </html>
        """
        
        self.wfile.write(html_content.encode())
        return
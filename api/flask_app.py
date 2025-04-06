from flask import Flask, redirect

app = Flask(__name__)

@app.route('/')
def home():
    return redirect('/index.html')

# This is just a backup fallback in case the ASGI app doesn't work
if __name__ == '__main__':
    app.run(debug=True)
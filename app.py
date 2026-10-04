"""
Spine Health Analytics & Risk Assessment Platform
--------------------------------------------------
Flask entry point. Serves the Stitch-designed dashboard pages and the
JSON API that powers them. Run with:  python app.py
"""
from flask import Flask

from backend.routes import bp


def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB upload cap
    app.register_blueprint(bp)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)

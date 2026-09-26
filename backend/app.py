import logging
import os
import shutil

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from routes.convert import convert_bp
from routes.download import download_bp
from routes.health import health_bp
from services.ffmpeg_service import FFmpegNotAvailableError

load_dotenv()


def _max_file_size_bytes() -> int:
    raw = os.getenv("MAX_FILE_SIZE_MB", "500")
    try:
        size_mb = int(raw)
        if size_mb <= 0:
            raise ValueError
    except ValueError:
        logging.warning("Invalid MAX_FILE_SIZE_MB=%r. Falling back to 500 MB.", raw)
        size_mb = 500
    return size_mb * 1024 * 1024


def create_app() -> Flask:
    app = Flask(__name__)

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000").strip()
    app.config["FRONTEND_URL"] = frontend_url
    app.config["MAX_CONTENT_LENGTH"] = _max_file_size_bytes()
    app.config["JSON_SORT_KEYS"] = False

    CORS(app, origins=[frontend_url])

    app.register_blueprint(health_bp)
    app.register_blueprint(download_bp)
    app.register_blueprint(convert_bp)

    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_too_large(_error):
        return jsonify(error="File is too large."), 413

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        return jsonify(error=error.description), error.code

    @app.errorhandler(FFmpegNotAvailableError)
    def handle_ffmpeg_error(_error):
        return jsonify(
            error="FFmpeg is not installed or is not available in PATH."
        ), 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        app.logger.exception("Unhandled server error: %s", error)
        return jsonify(error="Media conversion failed."), 500

    # Fail fast in logs without preventing the health endpoint from starting.
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        app.logger.warning(
            "FFmpeg and/or ffprobe is not available in PATH. "
            "Media conversion endpoints will return an informative error."
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

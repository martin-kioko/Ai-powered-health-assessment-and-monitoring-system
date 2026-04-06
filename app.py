"""
app.py — Application factory.

Local:    flask run  OR  python app.py
Railway:  gunicorn app:app --workers 2 --threads 2 --worker-class gthread --timeout 120
"""
import os
import logging
import logging.config
from datetime import timedelta
from flask import Flask, render_template, redirect, url_for


from config import config
from extensions import limiter, csrf
from database import init_db
from auth import seed_defaults, get_current_user
from risk_engine.ml_model import preload as preload_model

from routes.auth_routes    import auth_bp
from routes.patient_routes import patient_bp
from routes.doctor_routes  import doctor_bp
from routes.admin_routes   import admin_bp


def _configure_logging() -> None:
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            }
        },
        "root": {"level": "INFO", "handlers": ["console"]},
    })


def create_app(config_name: str | None = None) -> Flask:
    _configure_logging()
    log = logging.getLogger(__name__)

    if config_name is None:
        config_name = "development" if os.environ.get("FLASK_DEBUG", "false").lower() == "true" \
                      else "production"

    app = Flask(__name__)
    cfg = config[config_name]
    app.config.from_object(cfg)
    app.secret_key = cfg.SECRET_KEY
    app.permanent_session_lifetime = timedelta(hours=8)

    # ── Extensions ────────────────────────────────────────────────────────────
    limiter.init_app(app)
    csrf.init_app(app)

    # ── Database (single engine, pool reused across all requests) ─────────────
    init_db(cfg.DATABASE_URL)
    seed_defaults(
        cfg.ADMIN_EMAIL, cfg.ADMIN_PASSWORD,
        cfg.DOCTOR_EMAIL, cfg.DOCTOR_PASSWORD,
    )

    # ── ML model preloaded here — once, at startup, not on first request ──────
    log.info("Loading ML model…")
    preload_model(cfg.MODEL_PATH, cfg.SCALER_PATH)

    # ── Blueprints ────────────────────────────────────────────────────────────
    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(admin_bp)

    # ── Context processor ─────────────────────────────────────────────────────
    @app.context_processor
    def inject_user():
        return {"current_user": get_current_user()}

    # ── Core routes ───────────────────────────────────────────────────────────
    @app.route("/")
    def landing():
        user = get_current_user()
        return render_template("landing.html", user=user)

    app.add_url_rule("/", endpoint="main.landing", view_func=landing)

    @app.route("/healthz")
    def healthz():
        from flask import jsonify
        return jsonify({"status": "ok"}), 200

    # ── Error handlers ────────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404, message="Page not found."), 404

    @app.errorhandler(500)
    def server_error(e):
        log.exception("Internal server error")
        return render_template("error.html", code=500, message="Something went wrong."), 500

    @app.errorhandler(429)
    def rate_limited(e):
        return render_template("error.html", code=429,
                               message="Too many requests. Please wait a moment."), 429

    log.info("Application ready (config: %s)", config_name)
    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=app.config["DEBUG"], host="0.0.0.0", port=port)

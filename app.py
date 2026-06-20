"""
Entry point for the SPIT Student Council Finance Management Portal.

    python app.py                 # run dev server (http://127.0.0.1:5000)
    flask --app app init-db       # create tables
    python seed.py                # load demo data
"""
import os

from finance_portal import create_app

app = create_app(os.environ.get("FLASK_CONFIG", "development"))

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    app.run(host=host, port=port, debug=app.config.get("DEBUG", False))

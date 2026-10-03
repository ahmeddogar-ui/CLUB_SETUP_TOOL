from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.core.security import get_csrf_token

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["csrf_token"] = get_csrf_token

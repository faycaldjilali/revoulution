from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

DB_PATH = "boamp.db"

templates = Jinja2Templates(directory="templates")
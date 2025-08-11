from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="templates")

# Root route to serve chatbot page
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Terms and Privacy route
@app.get("/terms-and-privacy")
async def terms_and_privacy():
    return RedirectResponse(url="/static/terms/SOP_Legal_AI_Assistant_Terms_and_Privacy.pdf", status_code=302)

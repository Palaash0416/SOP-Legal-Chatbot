from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Canonical URL
@app.get("/terms-and-privacy")
async def terms_and_privacy():
    # Redirect to the static PDF
    return RedirectResponse(url="/static/terms/SOP_Legal_AI_Assistant_Terms_and_Privacy.pdf", status_code=302)

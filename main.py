from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
class ChatRequest(BaseModel):
    user_id: str
    user_input: str
    session_state: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    return {"response": sop_chatbot(request.user_id, request.user_input, request.session_state)}

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
    

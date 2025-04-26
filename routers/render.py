from fastapi import APIRouter, Request , status
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

templates = Jinja2Templates("templates")

router = APIRouter()

@router.get("/",response_class=HTMLResponse)
async def login(request:Request):
    return templates.TemplateResponse("login.html", {"request":request})

@router.get("/registro",response_class=HTMLResponse)
async def registro(request:Request):
    return templates.TemplateResponse("registro.html", {"request":request})

@router.get("/buscar",response_class=HTMLResponse)
async def buscar(request:Request):
    return templates.TemplateResponse("buscar.html", {"request":request})

@router.get("/inicio")
async def inicio(request: Request):
    """Página de inicio después del login"""
    user_name = request.query_params.get("user_name")  
    user_id = request.query_params.get("user_id")
    
    if not user_name:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)  
    
    return templates.TemplateResponse("inicio.html", {"request": request, "name": user_name.capitalize() , "user_id":user_id})

@router.get("/dashboard",response_class=HTMLResponse)
async def dashboard (request:Request):
    user_name = request.query_params.get("user_name")  
    return templates.TemplateResponse("dashboard.html", {"request":request, "name": user_name})

from fastapi import APIRouter, Request , status ,HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import json
from urllib.parse import unquote

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


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    productos_cookie = request.cookies.get("productos")
    user_name = request.cookies.get("user_name")
    
    if not productos_cookie or not user_name:
        return RedirectResponse(url="/inicio", status_code=status.HTTP_302_FOUND)
        
    try:
        productos = json.loads(unquote(productos_cookie))
        print(f"Productos en cookie -3 : {productos_cookie}")
        print(f"Nombre de usuario en cookie -3: {user_name}")
    except Exception as e:
        print(f"Error al deserializar productos: {e}")
        raise HTTPException(status_code=400, detail="Error al procesar los productos en las cookies")

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "name": user_name,
        "productos": productos
    })
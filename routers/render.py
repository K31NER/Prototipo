import json
from utils.utils import *
from urllib.parse import unquote
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import APIRouter, Request , status ,HTTPException, Depends,Response

# Asegúrate de que oauth2_scheme esté importado o definido
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

SECRET_KEY = Secret_key
ALGORITHM = Algortihm
EXPIRES_DELTA = Expire_delta

templates = Jinja2Templates("templates")

router = APIRouter()

@router.get("/",response_class=HTMLResponse)
async def login(request:Request):
    return templates.TemplateResponse("login.html", {"request":request})

@router.get("/registro",response_class=HTMLResponse)
async def registro(request:Request):
    return templates.TemplateResponse("registro.html", {"request":request})

@router.get("/inicio",response_class=HTMLResponse)
async def inicio(request: Request, user:dict = Depends(get_current_user)):
    """Página de inicio después del login"""
    user_name = user.get("sub")
    user_id = user.get("id")
    
    if not user_name:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)  
    
    return templates.TemplateResponse("inicio.html", {"request": request, "name": user_name.capitalize() , "user_id":user_id})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request,user:str = Depends(get_current_user)):
    productos_cookie = request.cookies.get("productos")
    user_name = request.cookies.get("user_name")
    
    if not productos_cookie or not user_name:
        return RedirectResponse(url="/inicio", status_code=status.HTTP_302_FOUND)
        
    try:
        productos = json.loads(unquote(productos_cookie))
        #print(f"Productos en cookie -3 : {productos_cookie}")
        print(f"Nombre de usuario en cookie -3: {user_name}")
    except Exception as e:
        print(f"Error al deserializar productos: {e}")
        raise HTTPException(status_code=400, detail="Error al procesar los productos en las cookies")

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "name": user_name,
        "productos": productos
    })
    
@router.get("/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    response.delete_cookie("productos")
    response.delete_cookie("user_name")
    return response


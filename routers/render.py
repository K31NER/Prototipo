import json
from utils.utils import *
from urllib.parse import unquote
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import APIRouter, Form, Query, Request , status ,HTTPException, Depends,Response

# Asegúrate de que oauth2_scheme esté importado o definido
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

SECRET_KEY = Secret_key
ALGORITHM = Algortihm
EXPIRES_DELTA = Expire_delta

templates = Jinja2Templates("templates")
templates.env.filters['format_cop'] = format_colombian_peso_manual

router = APIRouter()

@router.get("/",response_class=HTMLResponse)
async def login(request:Request):
    return templates.TemplateResponse("login.html", {"request":request})

@router.get("/registro",response_class=HTMLResponse)
async def registro(request:Request):
    return templates.TemplateResponse("registro.html", {"request":request})

@router.get("/verificacion",response_class=HTMLResponse)
async def verificacion(request:Request, correo: str = Query(...)):
    return templates.TemplateResponse("verificacion.html", {"request":request, "correo": correo})

@router.get("/contraseña",response_class=HTMLResponse)
async def contraseña(request:Request, correo: str = Query(...)):
    return templates.TemplateResponse("contraseña.html", {"request":request, "correo": correo})

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
        "name": user_name.capitalize(),
        "productos": productos
    })
    
@router.get("/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    response.delete_cookie("productos")
    response.delete_cookie("user_name")
    return response


@router.post("/recuperar_cuenta")
async def pedir_codigo(session:sesion, correo: str = Form(...)):
    # Obtenemos el correo del usuario
    email = correo
    
    # Preparamos la consulta
    consulta = select(User).where(User.correo == email)
    
    # Ejecutamos la consulta
    user = session.exec(consulta).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Correo no encontrado")
    code = generar_codigo()
    
    codigos_recuperacion[email] = code
    
    await enviar_correo(email,code)
    
    return RedirectResponse(url=f"/verificacion?correo={user.correo}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/validar_codigo")
async def validar_codigo(session: sesion, correo: str = Form(...),
                                          code1: str = Form(...),
                                          code2: str = Form(...),
                                          code3: str = Form(...),
                                          code4: str = Form(...),
                                          code5: str = Form(...),
                                          code6: str = Form(...)):
    
    email = correo
    code = f"{code1}{code2}{code3}{code4}{code5}{code6}"

    consulta = select(User).where(User.correo == email)
    print(f"email: {email}")
    user = session.exec(consulta).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Correo no encontrado")

    if email not in codigos_recuperacion or codigos_recuperacion[email] != code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código incorrecto")

    # Guardamos que el código fue validado para ese email
    codigos_validados[email] = True
    return RedirectResponse(url=f"/contraseña?correo={user.correo}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/cambiar_contraseña")
async def cambiar_contraseña(session: sesion, new_password: str = Form(...), correo: str = Form(...)):
    
    email = correo
    nueva_contraseña = new_password

    if email not in codigos_validados:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Código no validado o expirado")

    consulta = select(User).where(User.correo == email)
    user = session.exec(consulta).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    # Ciframos la contraseña y la actualizamos
    contraseña_cifrada = hash_contraseña(nueva_contraseña)
    user.contraseña = contraseña_cifrada

    session.add(user)
    session.commit()
    session.refresh(user)

    # Limpiamos los datos temporales
    codigos_validados.pop(email, None)
    codigos_recuperacion.pop(email, None)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    
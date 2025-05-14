import json
import asyncio
from db import sesion
from utils.utils import *
from slowapi import Limiter
from datetime import datetime
from urllib.parse import quote
from sqlalchemy.exc import SQLAlchemyError
from slowapi.util import get_remote_address
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse,JSONResponse
from perfil_de_usuarios import obtener_categoria_meta, generar_embedding
from fastapi import APIRouter, HTTPException, status,Form , Response, Request, Depends

SECRET_KEY = Secret_key
ALGORITHM = Algortihm
EXPIRES_DELTA = Expire_delta

# Schema de autentificacion
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

# Objeto router
router = APIRouter(prefix="/users",tags=["users"])

# Limitador de peticiones
limiter = Limiter(key_func=get_remote_address)

# Ubicacion de los templates
templates = Jinja2Templates(directory="templates")

# Bloqueador de session
registro_lock = asyncio.Lock()
@router.post("/registro",status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")  # Limitar registro a 5 peticiones por minuto
async def create_user(session: sesion, request:Request,
                    nombre: str = Form(...),
                    correo: str = Form(...),
                    genero: str = Form(...),
                    fecha_nacimiento: str = Form(...),
                    contraseña: str = Form(...),):
    """Crea un nuevo usuario, o muestra mensaje si ya existe el correo"""
    
    async with registro_lock:
        # Validar si el correo ya existe
        existing_user = session.execute(select(User).where(User.correo == correo)).scalar_one_or_none()

        if existing_user:
            return RedirectResponse(url=f"/registro?mensaje=Correo_existente", status_code=303)
        
        try:
            """ Crea un nuevo usuario """
            # Convertir fecha de string a objeto datetime
            fecha_nacimiento = datetime.strptime(fecha_nacimiento, "%Y-%m-%d").date()
            
            # Creamos el usuario en base al modelo 
            new_user = User(
                nombre=nombre,
                correo=correo,
                genero=genero,
                fecha_nacimiento=fecha_nacimiento, 
                contraseña=hash_contraseña(contraseña),
            )
            
            # Agregamos el usuario
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            
            # Creamos el token JWT
            user_data = {"sub": new_user.nombre, "id": new_user.id}
            access_token = create_jwt_token(user_data,SECRET_KEY,ALGORITHM,EXPIRES_DELTA)
            
            # redireccionamos al usuario a la página de inicio
            response = RedirectResponse(url=f"/inicio?user_name={new_user.nombre}&user_id={new_user.id}", status_code=status.HTTP_303_SEE_OTHER)
            # Creamos la cookie con el token
            response.set_cookie(key="access_token", value=access_token, httponly=True,secure=True, samesite='strict')
            
            return response
        except SQLAlchemyError as e:
            session.rollback()  # Limpiamos al session
            return RedirectResponse(url=f"/registro?mensaje=Error_registro", status_code=303)

@router.post("/login", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")  # Limitar registro a 5 peticiones por minuto
async def login(session: sesion,request:Request,
                nombre: str = Form(...), contraseña: str = Form(...)):
    """Función para verificar el usuario"""
    try:
        # Verificar si el usuario existe y la contraseña es correcta
        user = verificar_usuario(session, nombre, contraseña)
    except HTTPException as e:
        if e.status_code == status.HTTP_401_UNAUTHORIZED:
            return JSONResponse(content={"error": "Credenciales inválidas"}, status_code=status.HTTP_401_UNAUTHORIZED)
        raise e
    user_data:dict = {"sub":user.nombre, "id":user.id}
    access_token = create_jwt_token(user_data,SECRET_KEY,ALGORITHM,EXPIRES_DELTA)
    
    # redireccionamos al usuario a la página de inicio
    response = RedirectResponse(url=f"/inicio?user_name={user.nombre}&user_id={user.id}", status_code=status.HTTP_303_SEE_OTHER)
    # Creamos la cookie con el token
    response.set_cookie(key="access_token", value=access_token, httponly=True,secure=True, samesite='strict')
    
    return response

@router.post("/buscar")
@limiter.limit("3/minute")
async def buscar(
    request: Request,
    session: sesion,
    response: Response,
    producto: str = Form(...),
    id: str = Form(...),
    user = Depends(get_current_user),
):
    # 1. Realizamos el scrapeo
    busqueda_limpia = producto.lower().strip()
    if not busqueda_limpia:
        return RedirectResponse(
            url="/redirect_to_inicio?error=No se encontraron productos, realice otra búsqueda",
            status_code=303
        )
    datos = await hacer_peticion_scraper(busqueda_limpia)

    # Si no hay resultados, volvemos a la página de inicio con mensaje de error
    if not datos:
        return RedirectResponse(
            url="/redirect_to_inicio?error=No se encontraron productos, realice otra búsqueda",
            status_code=303
        )

    # 2. Buscar usuario
    user = session.get(User, id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # 3. Actualizamos el historial de búsqueda
    user.productos_buscados.append(busqueda_limpia)

    # 4. Actualizamos conteo de categorías
    if user.categorias_visitadas_raw is None:
        user.categorias_visitadas_raw = {}
    categoria = obtener_categoria_meta(busqueda_limpia)
    user.categorias_visitadas_raw[categoria] = (
        user.categorias_visitadas_raw.get(categoria, 0) + 1
    )

    # 5. Recalculamos el embedding
    embedding = generar_embedding(user.categorias_visitadas_raw)
    user.categorias_embedding = embedding

    # 6. Guardamos cambios en la base de datos
    session.add(user)
    session.commit()
    session.refresh(user)

    # 7. Procesamos los datos scrapeados
    try:
        productos_filtrados = preparar_datos(datos)
        if productos_filtrados.empty:
            raise ValueError("No hay datos válidos tras el preprocesamiento")
    except Exception as e:
        print(f"Error procesando los datos: {e}")
        return RedirectResponse(
            url="/redirect_to_inicio?error=No se encontraron productos, realice otra búsqueda",
            status_code=303
        )

    # 8. Creamos lista y la guardamos en cookie
    productos_lista = [
        {
            "nombre": p["Nombre"],
            "precio": p["Precio"],
            "puntuacion": p["Puntuacion"],
            "links": p["Links"],
        }
        for p in productos_filtrados.to_dict(orient="records")
    ]
    productos_json = quote(json.dumps(productos_lista))

    # 9. Redirigimos al dashboard
    response = RedirectResponse(
        url=f"/dashboard?user_name={user.nombre}&user_id={user.id}",
        status_code=303
    )
    # Creamos la cookie con los productos
    response.set_cookie("productos", productos_json, max_age=1800, httponly=True)
    response.set_cookie("user_name", user.nombre,   max_age=1800, httponly=True)
    return response


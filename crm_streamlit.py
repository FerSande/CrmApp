import streamlit as st
import jwt
import datetime
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Configuración de la base de datos
DATABASE_URL = "sqlite:///tasks.db"
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Define las clases para las tablas en la base de datos
class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)  # 'en proceso', 'finalizado', etc.
    hours_required = Column(Integer, nullable=False)

class State(Base):
    __tablename__ = 'states'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)

# Crea la base de datos y la tabla si no existen
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

# Configuración de JWT desde .env
SECRET_KEY = os.getenv("SECRET_KEY")  # Se toma del .env o se usa la predeterminada
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Función para generar el token JWT
def create_access_token(data: dict, expires_delta: datetime.timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Función para verificar el token JWT
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.JWTError:
        return None

# Función para obtener las credenciales del .env
def get_credentials():
    username = os.getenv("streamlit_user")  # Credenciales desde .env
    password = os.getenv("streamlit_pass")  # Contraseña desde .env
    return username, password

# Página de login (autenticación)
def login():
    st.title("Iniciar Sesión")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    # Obtener las credenciales almacenadas en el .env
    correct_username, correct_password = get_credentials()

    if st.button("Iniciar sesión"):
        # Verificar las credenciales del usuario con las del .env
        if username == correct_username and password == correct_password:
            # Generar el token
            access_token = create_access_token(data={"sub": username})
            # Almacenar el token en la sesión
            st.session_state["access_token"] = access_token
            st.session_state["username"] = username
            st.session_state["authenticated"] = True  # Indicar que el usuario está autenticado
            st.success("¡Sesión iniciada exitosamente!")
            # Establecer la bandera de redirección
            st.session_state["redirect_to_main"] = True
        else:
            st.error("Usuario o contraseña incorrectos.")

# Verificación de JWT en la sesión
def check_session():
    token = st.session_state.get("access_token")
    if token:
        user_data = verify_token(token)
        if user_data:
            return user_data["sub"]
    return None

# Página principal de la aplicación
def main():
    # Verificar si el usuario está autenticado
    if "redirect_to_main" in st.session_state and st.session_state["redirect_to_main"]:
        st.session_state["redirect_to_main"] = False  # Limpiar la bandera de redirección

    user = check_session()
    
    if not user:
        login()  # Si no está autenticado, mostrar la página de login
        return  # Terminar la ejecución de la app hasta que se inicie sesión
    
    # Si el usuario está autenticado, mostrar la aplicación
    st.write(f"Bienvenido, {user}!")

    # Barra lateral para navegación
    st.sidebar.title("Navegación")
    option = st.sidebar.selectbox("Selecciona una página", ["Inicio", "Añadir Tarea", "Ver Tareas", "Añadir Estados"])

    # Inicio
    if option == "Inicio":
        st.header("Bienvenido al CRM de Tareas")
        st.write("Usa la barra lateral para añadir o ver tareas.")

    # Añadir Tarea
    elif option == "Añadir Tarea":
        st.header("Agregar Nueva Tarea")
        title = st.text_input("Título")

        # Mostrar el desplegable de estados
        states = session.query(State).all()
        status_options = [state.name for state in states]
        status = st.selectbox("Estado", options=status_options)

        hours_required = st.number_input("Horas Requeridas", min_value=1, max_value=100, step=1)

        if st.button("Agregar Tarea"):
            if title and status:
                new_task = Task(title=title, status=status, hours_required=hours_required)
                session.add(new_task)
                session.commit()
                st.success("¡Tarea agregada exitosamente!")
            else:
                st.error("Por favor completa todos los campos.")

    # Ver Tareas
    elif option == "Ver Tareas":
        st.header("Lista de Tareas")

        # Buscador de tareas
        search_query = st.text_input("Buscar tarea por nombre")
        tasks = session.query(Task).filter(Task.title.contains(search_query)).all() if search_query else session.query(Task).all()

        if tasks:
            for task in tasks:
                with st.expander(task.title):
                    st.write(f"**Estado**: {task.status}")
                    st.write(f"**Horas Requeridas**: {task.hours_required}")

                    # Modificar tarea
                    # Botón único por tarea para evitar conflictos
                    with st.form(key=f"modify_form_{task.id}"):
                        new_title = st.text_input(f"Nuevo título para {task.title}", value=task.title)
                        new_status = st.selectbox(f"Nuevo estado para {task.title}", options=[task.status] + [state.name for state in session.query(State).all()])
                        new_hours = st.number_input(f"Nuevas horas para {task.title}", value=task.hours_required, min_value=1, max_value=100, step=1)

                        if st.form_submit_button(f"Guardar cambios para {task.title}"):
                            task.title = new_title
                            task.status = new_status
                            task.hours_required = new_hours
                            session.commit()
                            st.success(f"Tarea {task.title} modificada exitosamente!")

        else:
            st.write("No se encontraron tareas.")

    # Añadir Estados
    elif option == "Añadir Estados":
        st.header("Añadir Nuevo Estado")
        new_status = st.text_input("Escribe el nuevo estado")

        if st.button("Agregar Estado"):
            if new_status:
                existing_state = session.query(State).filter(State.name == new_status).first()
                if existing_state:
                    st.error(f"El estado '{new_status}' ya existe.")
                else:
                    new_state = State(name=new_status)
                    session.add(new_state)
                    session.commit()
                    st.success(f"Nuevo estado '{new_status}' agregado exitosamente.")
    
    # Cerrar sesión
    if st.button("Cerrar sesión"):
        # Eliminar el token y el usuario de la sesión
        del st.session_state["access_token"]
        del st.session_state["username"]
        del st.session_state["authenticated"]
        st.session_state["redirect_to_main"] = False  # Limpiar la bandera de redirección

# Ejecutar la aplicación
if __name__ == "__main__":
    main()

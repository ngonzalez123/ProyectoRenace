#RenaceHogaresVfinal
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_login import login_user, logout_user, login_required, current_user, LoginManager
from flask_migrate import Migrate
from sqlalchemy import and_, func
from flask_bcrypt import Bcrypt  #  Importa Flask-Bcrypt aquí
from models import db, Usuario, SolicitudAyuda, TicketSoporte, Respuesta, EstadoTicket, EstadoSolicitud, RolUsuario
from datetime import datetime
from forms import ResponderForm
# PRIMERO creas la app
app = Flask(__name__)
app.secret_key = "clave_super_secreta"

# LUEGO inicializas Bcrypt (después de crear la app)
bcrypt = Bcrypt(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:@localhost/proyecto_ayuda"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Inicializar correctamente
db.init_app(app)
migrate = Migrate(app, db)
#=============================================================
#BORRAR CACHE
@app.after_request
def add_header(response):
    """
    Agrega cabeceras para evitar que el navegador guarde páginas en caché.
    Esto previene que usuarios puedan volver atrás después de cerrar sesión.
    """
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

#=============================================================
with app.app_context():
    db.create_all()

# ======================
# Inicializar Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Debes iniciar sesión para acceder a esta página.'
login_manager.login_message_category = 'warning'

# Función de carga de usuario (¡CRÍTICA!)
# Flask-Login usa esta función para obtener el objeto Usuario a partir del ID de sesión.
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))
# ======================
# FUNCIONES AUXILIARES
# ======================
# def get_current_user():
#     """Obtiene el objeto Usuario completo basado en la sesión."""
#     # Asume que 'db' y 'session' (de Flask) y 'Usuario' (de models) están importados
#     if "usuario_id" not in session:
#         return None
#     # Usamos db.session.get para obtener el usuario
#     # Corregido: Si usas SQLAlchemy ORM, usa Usuario.query.get() o db.session.get()
#     return Usuario.query.get(session["usuario_id"])

def is_soporte(usuario):
    """Verifica si el usuario tiene el rol de soporte o administrador."""
    if not usuario:
        return False
    
    # CORREGIDO: Ahora verifica tanto ADMIN como SOPORTE
    return usuario.rol in [RolUsuario.ADMIN, RolUsuario.SOPORTE]

# =================================================================
# FUNCIÓN DE CONTEXTO (IMPORTANTE): INYECTA 'current_user' GLOBALMENTE
# ESTO SOLUCIONA EL ERROR: 'current_user' is undefined
# Asegúrate de que este bloque se coloque DESPUÉS de la inicialización de 'app'
# =================================================================
# @app.context_processor
# def inject_global_variables():
#     """Inyecta la variable 'current_user' en el contexto de Jinja para todas las plantillas."""
#     user = get_current_user()
    
#     # Devuelve un diccionario donde la clave es el nombre de la variable en Jinja
#     # y el valor es el objeto Usuario.
#     return dict(current_user=user)


#   RUTAS PRINCIPALES (index, registro, login, logout, perfil)
# ======================
@app.route('/')
def index():
    return render_template('index.html')


# ======================
#   REGISTRO DE USUARIOS
# ======================
@app.route('/registro', methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        cedula = request.form.get("cedula")
        nombre = request.form.get("nombre")
        apellido = request.form.get("apellido")
        email = request.form.get("email")
        telefono = request.form.get("telefono")
        direccion = request.form.get("direccion")
        municipio = request.form.get("municipio")
        password = request.form.get("password")

        # 🔒 Encriptar la contraseña antes de guardarla
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        nuevo_usuario = Usuario(
            cedula=cedula,
            nombre=nombre,
            apellido=apellido,
            email=email,
            telefono=telefono,
            direccion=direccion,
            municipio=municipio,
            password=hashed_password,  # ✅ Guarda la contraseña encriptada
            rol=RolUsuario.USUARIO
        )
        db.session.add(nuevo_usuario)
        db.session.commit()

        flash("Usuario registrado correctamente ✅", "success")
        return redirect(url_for('login'))

    return render_template('registro.html')

# ======================
#   LOGIN DE USUARIOS
# ======================
@app.route('/login', methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        cedula = request.form.get("cedula")
        password = request.form.get("password")

        usuario = Usuario.query.filter_by(cedula=cedula).first()

        if usuario and bcrypt.check_password_hash(usuario.password, password):
            login_user(usuario)
            flash("Inicio de sesión exitoso ✅", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Cédula o contraseña incorrecta ❌", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")


# ======================
#   DASHBOARD
# ======================
@app.route('/dashboard')
@login_required
def dashboard():
    # Flask-Login ya sabe quién está autenticado → current_user
    
    # Si el usuario es ADMIN, ve todas las solicitudes
    if current_user.rol == RolUsuario.ADMIN:
        solicitudes_query = SolicitudAyuda.query.order_by(SolicitudAyuda.id_solicitud.desc()).all()
    else:
        # Los usuarios normales ven solo sus propias solicitudes
        solicitudes_query = SolicitudAyuda.query.filter_by(id_usuario=current_user.id_usuario).order_by(SolicitudAyuda.id_solicitud.desc()).all()

    solicitudes_para_html = []
    for sol in solicitudes_query:
        # Obtener el nombre del creador (útil para que ADMIN sepa quién creó la solicitud)
        creador = Usuario.query.get(sol.id_usuario)
        nombre_creador = f"{creador.nombre} {creador.apellido}" if creador else "Usuario desconocido"
        
        solicitudes_para_html.append({
            "id": sol.id_solicitud,
            "tipo_desastre": sol.tipo_desastre,
            "fecha_desastre": sol.fecha_desastre,
            "direccion_afectada": sol.ubicacion,
            "personas_afectadas": sol.personas_afectadas,
            "prioridad": sol.prioridad,
            "descripcion_danos": sol.descripcion,
            "estado": sol.estado.name.capitalize().replace('_', ' '),
            "fecha_solicitud": getattr(sol, "fecha_creacion", datetime.now()),
            "creador_nombre": nombre_creador  # Nombre del usuario que creó la solicitud
        })

    return render_template(
        "dashboard.html",
        nombre=current_user.nombre,  # Usamos Flask-Login, no la sesión manual
        solicitudes=solicitudes_para_html
    )
# ======================
#   VER SOLICITUD
# ======================
@app.route('/ver_solicitud/<int:id>')
@login_required
def ver_solicitud(id):
    if not current_user.is_authenticated:
        flash("Debes iniciar sesión para crear una solicitud.", "warning")
        return redirect(url_for("login"))
    id_usuario = current_user.id_usuario

    # Buscar la solicitud y asegurarse de que pertenezca al usuario logueado
    # Usamos .first_or_404() para manejar el error de forma elegante
    solicitud = SolicitudAyuda.query.filter_by(id_solicitud=id, id_usuario=current_user.id_usuario).first_or_404()
    
    # Crear un objeto amigable para pasar al HTML
    data_solicitud = {
        'id': solicitud.id_solicitud,
        'tipo_desastre': solicitud.tipo_desastre,
        'fecha_desastre': solicitud.fecha_desastre,
        'ubicacion': solicitud.ubicacion,
        'personas_afectadas': solicitud.personas_afectadas,
        'prioridad': solicitud.prioridad,
        'descripcion': solicitud.descripcion,
        'estado': solicitud.estado.name.capitalize().replace('_', ' ')
    }

    return render_template("ver_solicitud.html", solicitud=data_solicitud)


# ======================
#   EDITAR SOLICITUD
# ======================
@app.route('/editar_solicitud/<int:id>', methods=["GET", "POST"])
@login_required
def editar_solicitud(id):
    if not current_user.is_authenticated:
        flash("Debes iniciar sesión para crear una solicitud.", "warning")
        return redirect(url_for("login"))
    id_usuario = current_user.id_usuario

    # 1. Buscar la solicitud y verificar permisos y estado
    solicitud = SolicitudAyuda.query.filter_by(id_solicitud=id, id_usuario=current_user.id_usuario).first_or_404()

    # CORREGIDO: Comprobar el estado del ENUM EstadoSolicitud.PENDIENTE
    if solicitud.estado != EstadoSolicitud.PENDIENTE:
        flash(f"La solicitud #{id} no se puede editar porque está en estado '{solicitud.estado.name.capitalize().replace('_', ' ')}'. Solo se permiten cambios en estado Pendiente.", "warning")
        return redirect(url_for("ver_solicitud", id=id))

    if request.method == "POST":
        # 2. PROCESAR EL FORMULARIO DE EDICIÓN
        try:
            # Obtener y validar datos
            solicitud.tipo_desastre = request.form.get("tipo_desastre")
            fecha_desastre_str = request.form.get("fecha_desastre")
            solicitud.ubicacion = request.form.get("direccion_afectada") 
            personas_afectadas_str = request.form.get("personas_afectadas")
            solicitud.prioridad = request.form.get("prioridad")
            solicitud.descripcion = request.form.get("descripcion_danos") 
            
            # Conversión de datos
            solicitud.fecha_desastre = datetime.strptime(fecha_desastre_str, '%Y-%m-%d').date()
            solicitud.personas_afectadas = int(personas_afectadas_str)

            # 3. Guardar cambios
            db.session.commit()
            flash(f"Solicitud #{id} actualizada exitosamente ✅", "success")
            return redirect(url_for("ver_solicitud", id=id))
        
        except ValueError:
            db.session.rollback()
            flash("Error en el formato de la fecha o el número de personas.", "danger")
            return redirect(url_for("editar_solicitud", id=id))
        except Exception as e:
             # Manejo de otros errores de base de datos o validación
            db.session.rollback()
            flash(f"Ocurrió un error al guardar: {e}", "danger")
            return redirect(url_for("editar_solicitud", id=id))


    # 4. RENDERIZAR EL FORMULARIO (GET)
    # Crear un objeto amigable para pasar al HTML
    data_solicitud = {
        'id': solicitud.id_solicitud,
        'tipo_desastre': solicitud.tipo_desastre,
        'fecha_desastre': solicitud.fecha_desastre,
        'direccion_afectada': solicitud.ubicacion, 
        'personas_afectadas': solicitud.personas_afectadas,
        'prioridad': solicitud.prioridad,
        'descripcion_danos': solicitud.descripcion,
        'estado': solicitud.estado.name.capitalize().replace('_', ' ')
    }

    return render_template("editar_solicitud.html", solicitud=data_solicitud)

#=============
#Elimina Solicitud
#============
@app.route('/eliminar_solicitud/<int:id_solicitud>', methods=["POST"])
@login_required
def eliminar_solicitud(id_solicitud):
    if not current_user.is_authenticated:
        flash("Debes iniciar sesión para crear una solicitud.", "warning")
        return redirect(url_for("login"))
    id_usuario = current_user.id_usuario
    
    solicitud = SolicitudAyuda.query.filter_by(id_solicitud=id_solicitud, id_usuario=current_user.id_usuario).first_or_404()

    # CORREGIDO: Comprobar el estado del ENUM EstadoSolicitud.PENDIENTE
    if solicitud.estado != EstadoSolicitud.PENDIENTE:
        flash(f"La solicitud #{id_solicitud} no se puede eliminar porque está en estado '{solicitud.estado.name.capitalize().replace('_', ' ')}'. Solo se permite eliminar en estado Pendiente.", "warning")
        return redirect(url_for("ver_solicitud", id=id_solicitud))
    

    try:
        db.session.delete(solicitud)
        db.session.commit()
        flash(f"Solicitud #{id_solicitud} eliminada exitosamente ✅", "success")
        return redirect(url_for("dashboard"))
    
    except Exception as e:
        db.session.rollback() 
        flash(f"Ocurrió un error al eliminar la solicitud: {e}", "danger")
        return redirect(url_for("ver_solicitud", id=id_solicitud))
#==================
#==================
#   CREAR SOLICITD
# ======================

@app.route('/nueva_solicitud', methods=["GET", "POST"])
@login_required
def nueva_solicitud():
    if not current_user.is_authenticated:
        flash("Debes iniciar sesión para crear una solicitud.", "warning")
        return redirect(url_for("login"))
    id_usuario = current_user.id_usuario

    if request.method == "POST":
        # 1. Obtener todos los campos del formulario, USANDO LOS NOMBRES EXACTOS DEL HTML
        tipo_desastre = request.form.get("tipo_desastre")
        fecha_desastre_str = request.form.get("fecha_desastre") 
        direccion_afectada = request.form.get("direccion_afectada") 
        personas_afectadas_str = request.form.get("personas_afectadas")
        prioridad = request.form.get("prioridad")
        descripcion_danos = request.form.get("descripcion_danos")
        

        # 2. Validación de campos obligatorios 
        if (not tipo_desastre or tipo_desastre.strip() == "") or \
           (not fecha_desastre_str or fecha_desastre_str.strip() == "") or \
           (not direccion_afectada or direccion_afectada.strip() == "") or \
           (not descripcion_danos or descripcion_danos.strip() == ""):
           
           flash("Por favor completa los campos obligatorios marcados (*).", "danger")
           return redirect(url_for("nueva_solicitud")) 

        try:
            # 3. CONVERSIÓN DE FECHA
            fecha_desastre_obj = datetime.strptime(fecha_desastre_str, '%Y-%m-%d').date()
            
            # 4. CONVERSIÓN DE ENTEROS
            personas_afectadas = int(personas_afectadas_str) if personas_afectadas_str and personas_afectadas_str.isdigit() else None

        except ValueError:
            flash("Error en el formato de la fecha o el número de personas. Asegúrate de que las personas afectadas sea un número entero.", "danger")
            return redirect(url_for("nueva_solicitud"))

        # 5. Insertar en la tabla SolicitudAyuda, mapeando los nombres del formulario
        nueva_solicitud = SolicitudAyuda(
            id_usuario=id_usuario,
            descripcion=descripcion_danos, 
            ubicacion=direccion_afectada, 
            tipo_desastre=tipo_desastre,
            fecha_desastre=fecha_desastre_obj, 
            personas_afectadas=personas_afectadas,
            prioridad=prioridad,
            # Aseguramos el Estado por defecto
            estado=EstadoSolicitud.PENDIENTE
        )

        db.session.add(nueva_solicitud)
        db.session.commit()

        flash("Solicitud de ayuda enviada exitosamente ✅", "success")
        return redirect(url_for("dashboard"))

    # Si es GET, renderiza el formulario
    return render_template("nueva_solicitud.html")
# ======================================================



# ======================================================
#   CREAR TICKET DE SOPORTE
# ======================================================
@app.route('/crear_ticket', methods=['GET', 'POST'])
@login_required
def crear_ticket():
    if not current_user.is_authenticated:
        flash("Debes iniciar sesión para crear una solicitud.", "warning")
        return redirect(url_for("login"))
    id_usuario = current_user.id_usuario

    if request.method == 'POST':
        asunto = request.form['asunto']
        descripcion = request.form['descripcion']

        # Usamos el constructor asumiendo la estructura de columna del modelo original,
        # pero pasándole el objeto ENUM correcto, que es lo que hace SQLAlchemy.
        # Si tu base de datos espera un ID, el ORM de SQLAlchemy lo manejará.
        nuevo_ticket = TicketSoporte(
            id_usuario=current_user.id_usuario,
            asunto=asunto,
            descripcion=descripcion,
            estado=EstadoTicket.ABIERTO  # Pasamos el objeto ENUM
        )

        db.session.add(nuevo_ticket)
        db.session.commit()

        flash("Tu ticket de soporte ha sido creado exitosamente.", "success")
        return redirect(url_for('mis_tickets'))

    # Esta ruta debería apuntar a la plantilla crear_ticket.html
    return render_template('crear_ticket.html')

#======================
# VER TODOS TICKETS SOPORTE (CORREGIDA)
#=======================
@app.route('/tickets')
@login_required
def mis_tickets():
    # Si el usuario es ADMIN o SOPORTE, ve todos los tickets
    if current_user.rol in [RolUsuario.ADMIN, RolUsuario.SOPORTE]:
        tickets = TicketSoporte.query.order_by(TicketSoporte.id_ticket.desc()).all()
    else:
        # Los usuarios normales ven solo sus propios tickets
        tickets = (
            TicketSoporte.query
            .filter_by(id_usuario=current_user.id_usuario)
            .order_by(TicketSoporte.id_ticket.desc())
            .all()
        )

    # Preparar los datos para la plantilla
    tickets_para_html = []
    for ticket in tickets:
        # Obtener el nombre del creador
        nombre_creador = (
            ticket.creador_ticket.nombre_completo if hasattr(ticket, "creador_ticket") and ticket.creador_ticket
            else f"ID Usuario: {ticket.id_usuario}"
        )

        tickets_para_html.append({
            "id_ticket": ticket.id_ticket,
            "asunto": ticket.asunto,
            "estado": ticket.estado.name.capitalize().replace("_", " "),
            "creador_nombre": nombre_creador,
            "fecha_creacion": ticket.fecha_creacion  # Agregar fecha para mostrarla
        })

    # Renderizar la plantilla con los datos listos
    return render_template("mis_tickets.html", tickets=tickets_para_html)

# ======================
#   DETALLES DE TICKET (ver_ticket.html) (CORREGIDA)
# ======================
@app.route('/ticket/<int:id_ticket>', methods=['GET', 'POST'])
@login_required
def ver_ticket(id_ticket):
    ticket = db.session.get(TicketSoporte, id_ticket)
    if not ticket:
        flash('Ticket no encontrado.', 'danger')
        return redirect(url_for('dashboard', tab='tickets'))
        
    # 1. Instanciar el formulario de respuesta
    form = ResponderForm()

    # 2. Lógica para manejar el envío del formulario POST
    if form.validate_on_submit():
        # Verificar que el usuario sea ADMIN o SOPORTE
        if current_user.rol not in [RolUsuario.ADMIN, RolUsuario.SOPORTE]:
            flash('No tienes permisos para responder tickets.', 'error')
            return redirect(url_for('ver_ticket', id_ticket=id_ticket))
        
        if ticket.estado != EstadoTicket.CERRADO:
            try:
                # Crear el nuevo objeto Respuesta
                nueva_respuesta = Respuesta(
                    id_usuario=current_user.id_usuario,
                    id_ticket=ticket.id_ticket,
                    mensaje=form.mensaje.data,
                    fecha=datetime.utcnow()
                )
                db.session.add(nueva_respuesta)
                
                # Regla de Negocio: Si un SOPORTE responde a un ticket ABIERTO,
                # cámbialo a EN_PROCESO para indicar que está siendo atendido.
                if current_user.rol == RolUsuario.SOPORTE and ticket.estado == EstadoTicket.ABIERTO:
                    ticket.estado = EstadoTicket.EN_PROCESO
                
                db.session.commit()
                flash('Respuesta enviada correctamente.', 'success')
                # PRG Pattern: Redirigir después de POST exitoso
                return redirect(url_for('ver_ticket', id_ticket=ticket.id_ticket))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al enviar respuesta: {str(e)}', 'danger')
        else:
            flash('No se puede responder a un ticket cerrado.', 'warning')
            
    # 3. Renderizar la plantilla
    return render_template(
        'ver_ticket.html', 
        ticket=ticket, 
        form=form
    )

#===========================
#actualizar_ticket (CORREGIDA)
#===========================
@app.route('/actualizar_ticket/<int:id_ticket>', methods=['POST'])
@login_required
def actualizar_ticket(id_ticket):
    """
    Maneja el envío de una nueva respuesta y el posible cambio de estado del ticket.
    NOTA: Se ha adaptado para usar Flask-SQLAlchemy y los modelos.
    """
    # 1. Obtener usuario y verificar login
    if not current_user.is_authenticated:
        flash("Por favor inicia sesión...", "warning")
        return redirect(url_for("login"))
    usuario_actual = current_user
        
    ticket = TicketSoporte.query.filter_by(id_ticket=id_ticket).first_or_404()

    mensaje = request.form.get('mensaje')
    accion = request.form.get('accion') # Usaremos un campo oculto 'accion' para cerrar/reabrir (e.g., 'cerrar' o 'reabrir')
    
    # Verificar permisos
    es_solicitante = ticket.id_usuario == usuario_actual.id_usuario
    es_soporte_user = is_soporte(usuario_actual)
    
    if not es_solicitante and not es_soporte_user:
        flash('No tienes permiso para actualizar este ticket.', 'danger')
        return redirect(url_for('ver_ticket', id_ticket=id_ticket))

    try:
        # 1. Manejar Respuesta
        if mensaje and mensaje.strip():
            # Permitir respuesta si el ticket está abierto o si el usuario es Soporte
            if ticket.estado == EstadoTicket.CERRADO and not es_soporte_user:
                 flash("No se pueden enviar respuestas a un ticket cerrado (solo Soporte puede reabrirlo).", "danger")
            else:
                nueva_respuesta = Respuesta(
                    id_ticket=id_ticket,
                    id_usuario=usuario_actual.id_usuario, 
                    mensaje=mensaje,
                    fecha=datetime.utcnow()
                )
                db.session.add(nueva_respuesta)
                
                # Regla de negocio: Si alguien responde a un ticket cerrado/pendiente, se marca como ABIERTO
                if ticket.estado != EstadoTicket.ABIERTO:
                     ticket.estado = EstadoTicket.ABIERTO
                     
                flash('Mensaje enviado exitosamente.', 'success')

        # 2. Manejar Acciones de Estado (Solo para Soporte)
        if es_soporte_user:
            if accion == 'cerrar':
                if ticket.estado != EstadoTicket.CERRADO:
                    ticket.estado = EstadoTicket.CERRADO
                    flash(f'Ticket #{id_ticket} cerrado correctamente.', 'info')
                else:
                    flash('El ticket ya estaba cerrado.', 'warning')
                    
            elif accion == 'reabrir':
                if ticket.estado == EstadoTicket.CERRADO:
                    ticket.estado = EstadoTicket.ABIERTO 
                    flash(f'Ticket #{id_ticket} reabierto correctamente.', 'info')
                else:
                    flash('El ticket no está cerrado para reabrirlo.', 'warning')

        db.session.commit()
        
        if not mensaje and not accion:
             # Este caso es solo si el usuario envía el formulario vacío
             flash('No se realizó ninguna acción (mensaje vacío o acción no reconocida).', 'warning')
             
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar el ticket: {e}', 'danger')

    return redirect(url_for('ver_ticket', id_ticket=id_ticket))
#============================================================================
#==================
## CERRAR TICKETS
#================
@app.route('/ticket/<int:id_ticket>/cerrar', methods=['POST'])
@login_required
def cerrar_ticket(id_ticket):
    # Buscar el ticket (CORREGIDO: Usa TicketSoporte, no Ticket)
    ticket = TicketSoporte.query.get_or_404(id_ticket)
    
    # Verificar que el usuario sea ADMIN o SOPORTE (CORREGIDO: Usa el ENUM RolUsuario)
    if current_user.rol not in [RolUsuario.ADMIN, RolUsuario.SOPORTE]:
        flash('No tienes permisos para cerrar tickets. Solo ADMIN y SOPORTE pueden hacerlo.', 'error')
        return redirect(url_for('ver_ticket', id_ticket=id_ticket))
    
    # Verificar que el ticket no esté ya cerrado (CORREGIDO: Usa el ENUM EstadoTicket)
    if ticket.estado == EstadoTicket.CERRADO:
        flash('Este ticket ya está cerrado.', 'warning')
        return redirect(url_for('ver_ticket', id_ticket=id_ticket))
    
    # Cerrar el ticket (CORREGIDO: Usa el ENUM EstadoTicket)
    ticket.estado = EstadoTicket.CERRADO
    ticket.fecha_cierre = datetime.now()  # Opcional: si tienes este campo
    
    db.session.commit()
    
    flash('Ticket cerrado exitosamente.', 'success')
    return redirect(url_for('ver_ticket', id_ticket=id_ticket))

#==================
## REABRIR TICKETS
#================
@app.route('/ticket/<int:id_ticket>/reabrir', methods=['POST'])
@login_required
def reabrir_ticket(id_ticket):
    # Buscar el ticket
    ticket = TicketSoporte.query.get_or_404(id_ticket)
    
    # Verificar que el usuario sea ADMIN o SOPORTE
    if current_user.rol not in [RolUsuario.ADMIN, RolUsuario.SOPORTE]:
        flash('No tienes permisos para reabrir tickets. Solo ADMIN y SOPORTE pueden hacerlo.', 'error')
        return redirect(url_for('ver_ticket', id_ticket=id_ticket))
    
    # Verificar que el ticket esté cerrado
    if ticket.estado != EstadoTicket.CERRADO:
        flash('Este ticket ya está abierto.', 'warning')
        return redirect(url_for('ver_ticket', id_ticket=id_ticket))
    
    # Reabrir el ticket
    ticket.estado = EstadoTicket.ABIERTO
    
    db.session.commit()
    
    flash('Ticket reabierto exitosamente.', 'success')
    return redirect(url_for('ver_ticket', id_ticket=id_ticket))

#======================================================================================================================
# ======================
#   CERRAR SESIÓN
# ======================
@app.route('/logout')
def logout():
    logout_user()  # Limpia la sesión de Flask-Login
    flash("Sesión cerrada correctamente ", "info")
    return redirect(url_for("index"))


@app.route('/perfil')
@login_required
def perfil():
    return render_template("perfil.html", usuario=current_user)


# ======================
#   EJECUTAR SERVIDOR
# ======================
if __name__ == "__main__":
    app.run(debug=True)
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_login import login_user, logout_user, login_required, current_user, LoginManager
from flask_migrate import Migrate
from sqlalchemy import and_, func
from flask_bcrypt import Bcrypt  #  Importa Flask-Bcrypt aquí
from models import db, Usuario, SolicitudAyuda, TicketSoporte, Respuesta, EstadoTicket, EstadoSolicitud, RolUsuario

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
def get_current_user():
    """Obtiene el objeto Usuario completo basado en la sesión."""
    # Asume que 'db' y 'session' (de Flask) y 'Usuario' (de models) están importados
    if "usuario_id" not in session:
        return None
    # Usamos db.session.get para obtener el usuario
    # Corregido: Si usas SQLAlchemy ORM, usa Usuario.query.get() o db.session.get()
    return Usuario.query.get(session["usuario_id"])

def is_soporte(usuario):
    """Verifica si el usuario tiene el rol de soporte o administrador."""
    # Corregido: Para que el usuario de soporte vea los tickets, debe chequear
    # SOPORTE o ADMIN (si ADMIN también maneja soporte).
    if not usuario:
        return False
        
    return usuario.rol == RolUsuario.ADMIN

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
    solicitudes_query = SolicitudAyuda.query.filter_by(id_usuario=current_user.id_usuario).order_by(SolicitudAyuda.id_solicitud.desc()).all()

    solicitudes_para_html = []
    for sol in solicitudes_query:
        solicitudes_para_html.append({
            "id": sol.id_solicitud,
            "tipo_desastre": sol.tipo_desastre,
            "fecha_desastre": sol.fecha_desastre,
            "direccion_afectada": sol.ubicacion,
            "personas_afectadas": sol.personas_afectadas,
            "prioridad": sol.prioridad,
            "descripcion_danos": sol.descripcion,
            "estado": sol.estado.name.capitalize().replace('_', ' '),
            "fecha_solicitud": getattr(sol, "fecha_creacion", datetime.now())
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
def ver_solicitud(id):
    if "usuario_id" not in session:
        flash("Por favor inicia sesión para continuar.", "warning")
        return redirect(url_for("login"))

    # Buscar la solicitud y asegurarse de que pertenezca al usuario logueado
    # Usamos .first_or_404() para manejar el error de forma elegante
    solicitud = SolicitudAyuda.query.filter_by(id_solicitud=id, id_usuario=session["usuario_id"]).first_or_404()
    
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
def editar_solicitud(id):
    if "usuario_id" not in session:
        flash("Debes iniciar sesión para editar una solicitud.", "warning")
        return redirect(url_for("login"))

    # 1. Buscar la solicitud y verificar permisos y estado
    solicitud = SolicitudAyuda.query.filter_by(id_solicitud=id, id_usuario=session["usuario_id"]).first_or_404()

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
def eliminar_solicitud(id_solicitud):
    if "usuario_id" not in session:
        flash("Debes iniciar sesión para eliminar una solicitud.", "warning")
        return redirect(url_for("login"))
    
    solicitud = SolicitudAyuda.query.filter_by(id_solicitud=id_solicitud, id_usuario=session["usuario_id"]).first_or_404()

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
def nueva_solicitud():
    if "usuario_id" not in session:
        flash("Debes iniciar sesión para crear una solicitud.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        # 1. Obtener todos los campos del formulario, USANDO LOS NOMBRES EXACTOS DEL HTML
        tipo_desastre = request.form.get("tipo_desastre")
        fecha_desastre_str = request.form.get("fecha_desastre") 
        direccion_afectada = request.form.get("direccion_afectada") 
        personas_afectadas_str = request.form.get("personas_afectadas")
        prioridad = request.form.get("prioridad")
        descripcion_danos = request.form.get("descripcion_danos")
        id_usuario = session["usuario_id"]

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
def crear_ticket():
    if "usuario_id" not in session:
        flash("Debes iniciar sesión para crear un ticket de soporte.", "warning")
        return redirect(url_for("login"))

    if request.method == 'POST':
        asunto = request.form['asunto']
        descripcion = request.form['descripcion']

        # Usamos el constructor asumiendo la estructura de columna del modelo original,
        # pero pasándole el objeto ENUM correcto, que es lo que hace SQLAlchemy.
        # Si tu base de datos espera un ID, el ORM de SQLAlchemy lo manejará.
        nuevo_ticket = TicketSoporte(
            id_usuario=session["usuario_id"],
            asunto=asunto,
            descripcion=descripcion,
            estado=EstadoTicket.ABIERTO  # Pasamos el objeto ENUM
        )

        db.session.add(nuevo_ticket)
        db.session.commit()

        flash("Tu ticket de soporte ha sido creado exitosamente.", "success")
        return redirect(url_for('dashboard'))

    # Esta ruta debería apuntar a la plantilla crear_ticket.html
    return render_template('crear_ticket.html')

#======================
# VER TICKETS SOPORTE (CORREGIDA)
#=======================
@app.route('/tickets')
def mis_tickets():
    # 1. Solución NameError: La función auxiliar ya está definida arriba.
    usuario_actual = get_current_user()
    if not usuario_actual:
        flash("Por favor inicia sesión para acceder a tus tickets.", "warning")
        return redirect(url_for("login"))
    
    # 2. Lógica de filtrado de tickets: corregir nombre de la clase y el filtro de rol
    if is_soporte(usuario_actual):
        # Soporte (admin) ve todos los tickets
        # Corregido: Ordenamos por id_ticket ya que fecha_apertura no existe.
        tickets = TicketSoporte.query.order_by(TicketSoporte.id_ticket.desc()).all()
    else:
        # Usuarios normales ven solo los tickets que crearon
        # Corregido: Ordenamos por id_ticket ya que fecha_apertura no existe.
        tickets = TicketSoporte.query.filter_by(
            id_usuario=usuario_actual.id_usuario
        ).order_by(TicketSoporte.id_ticket.desc()).all()


    # 3. Formatear la lista de tickets para la plantilla (es lo que espera mis_tickets.html)
    tickets_para_html = []
    for ticket in tickets:
        # Corregido: Si no tienes la relación 'creador' definida en models.py
        # no se puede acceder a ticket.creador.nombre. Para evitar errores,
        # lo cambiamos a una comprobación segura o a un valor por defecto.
        # Asumiendo que has definido la relación 'creador' en models.py:
        # creador = db.relationship('Usuario', backref='tickets', foreign_keys=[id_usuario])
        
        # Si TicketSoporte tiene una relación 'creador'
        if hasattr(ticket, 'creador') and ticket.creador:
            nombre_creador = ticket.creador.nombre
        else:
            # Caso de respaldo si la relación no existe o falla
            nombre_creador = f"ID Usuario: {ticket.id_usuario}"
        
        # IMPORTANTE: Ya que eliminamos fecha_apertura de la BD, no podemos acceder a ella. 
        # Si necesitas mostrar la fecha de creación, DEBES tener una columna de fecha.
        # Por ahora, la omitiremos para evitar errores, o usaremos una marca de tiempo si existe otra.
        
        tickets_para_html.append({
            'id_ticket': ticket.id_ticket,
            'asunto': ticket.asunto,
            'estado': ticket.estado.name.capitalize().replace('_', ' '),
            # Quitamos la referencia a fecha_apertura para evitar el AttributeError:
            # 'fecha_apertura': ticket.fecha_apertura.strftime('%Y-%m-%d %H:%M') if ticket.fecha_apertura else 'N/A',
            'creador_nombre': nombre_creador
        })

    # Renderiza la plantilla que lista los tickets
    return render_template(
        "mis_tickets.html", 
        tickets=tickets_para_html, # Pasamos la lista formateada
        usuario_actual=usuario_actual
    )

# ======================
#   RUTA 2: DETALLES DE TICKET (ver_ticket.html) (CORREGIDA)
# ======================
@app.route('/ticket/<int:id_ticket>', methods=['GET', 'POST'])
@login_required
def ver_ticket(id_ticket):
    ticket = db.session.get(TicketSoporte, id_ticket)
    if not ticket:
        flash('Ticket no encontrado.', 'danger')
        return redirect(url_for('dashboard', tab='tickets'))
        
    # 1. Instanciar el formulario de respuesta (CORRECCIÓN CLAVE)
    form = RespuestaForm() 
    
    # 2. Determinar si el usuario es de Soporte para los permisos en HTML
    # (Asegúrate de que current_user.rol existe y tiene un .name)
    es_soporte = current_user.rol.name == 'SOPORTE' if current_user.rol else False

    # 3. Lógica para manejar el envío del formulario POST
    if form.validate_on_submit():
        if ticket.estado.name != 'CERRADO':
            try:
                # Crea el nuevo objeto Respuesta
                nueva_respuesta = Respuesta(
                    id_usuario=current_user.id_usuario,
                    id_ticket=ticket.id_ticket,
                    mensaje=form.mensaje.data,
                    fecha=datetime.utcnow()
                )
                db.session.add(nueva_respuesta)
                
                # Regla de Negocio: Si un Soporte responde a un ticket ABIERTO,
                # cámbialo a EN_PROCESO para indicar que está siendo atendido.
                if es_soporte and ticket.estado.name == 'ABIERTO':
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
            
    # 4. Renderizar la plantilla, pasando el ticket, el formulario y es_soporte
    return render_template(
        'ver_ticket.html', 
        ticket=ticket, 
        form=form, # <-- ¡LA VARIABLE QUE FALTABA!
        es_soporte=es_soporte
    )

#===========================
#actualizar_ticket (CORREGIDA)
#===========================
@app.route('/actualizar_ticket/<int:id_ticket>', methods=['POST'])
def actualizar_ticket(id_ticket):
    """
    Maneja el envío de una nueva respuesta y el posible cambio de estado del ticket.
    NOTA: Se ha adaptado para usar Flask-SQLAlchemy y los modelos.
    """
    # 1. Obtener usuario y verificar login
    usuario_actual = get_current_user()
    if not usuario_actual:
        flash('Debes iniciar sesión para interactuar con los tickets.', 'warning')
        return redirect(url_for('login'))
        
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


# ======================
#   CERRAR SESIÓN
# ======================
@app.route('/logout')
def logout():
    logout_user()  # Limpia la sesión de Flask-Login
    flash("Sesión cerrada correctamente ", "info")
    return redirect(url_for("index"))


@app.route('/perfil')
def perfil():
    if "usuario_id" not in session: # <--- Esto es la corrección del corte
        flash("Debes iniciar sesión para ver tu perfil.", "warning")
        return redirect(url_for("login"))

    usuario = get_current_user()
    if not usuario:
        flash("Usuario no encontrado.", "danger")
        session.clear()
        return redirect(url_for("login"))

    # Aquí puedes agregar la lógica para mostrar el perfil
    return render_template("perfil.html", usuario=usuario)


# ======================
#   EJECUTAR SERVIDOR
# ======================
if __name__ == "__main__":
    app.run(debug=True)
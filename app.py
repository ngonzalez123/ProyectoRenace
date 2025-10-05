from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, Usuario, SolicitudAyuda, TicketSoporte, Respuesta

from datetime import datetime # ¡Necesitamos datetime para manejar las fechas!


app = Flask(__name__)
app.secret_key = "clave_super_secreta"

# 🔗 Configuración de conexión con MySQL (ajusta si tienes contraseña)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:@localhost/proyecto_ayuda"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# Inicializar conexión
db.init_app(app)

# Crear las tablas (solo la primera vez)
with app.app_context():
    db.create_all()

# ======================
#   RUTA DE INICIO
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

        nuevo_usuario = Usuario(
            cedula=cedula,
            nombre=nombre,
            apellido=apellido,
            email=email,
            telefono=telefono,
            direccion=direccion,
            municipio=municipio,
            password=password
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
    if request.method == "POST":
        cedula = request.form.get("cedula")
        password = request.form.get("password")

        usuario = Usuario.query.filter_by(cedula=cedula, password=password).first()

        if usuario:
            session["usuario_id"] = usuario.id_usuario
            session["usuario_nombre"] = usuario.nombre
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
def dashboard():
    if "usuario_id" not in session:
        flash("Por favor inicia sesión para continuar.", "warning")
        return redirect(url_for("login"))
    return render_template("dashboard.html", nombre=session["usuario_nombre"])


# ======================
#   CREAR SOLICITD
# ======================
# -----------------------------------------------------
# RUTA CORREGIDA: CREAR SOLICITUD DE AYUDA
# -----------------------------------------------------

@app.route('/nueva_solicitud', methods=["GET", "POST"])
def nueva_solicitud():
    if "usuario_id" not in session:
        flash("Debes iniciar sesión para crear una solicitud.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        # 1. Obtener todos los campos del formulario, USANDO LOS NOMBRES EXACTOS DEL HTML
        tipo_desastre = request.form.get("tipo_desastre")
        fecha_desastre_str = request.form.get("fecha_desastre") 
        
        # OBTENIENDO DEL FORMULARIO: <input name="direccion_afectada">
        direccion_afectada = request.form.get("direccion_afectada") 
        
        personas_afectadas_str = request.form.get("personas_afectadas")
        prioridad = request.form.get("prioridad")
        
        # OBTENIENDO DEL FORMULARIO: <textarea name="descripcion_danos">
        descripcion_danos = request.form.get("descripcion_danos")
        
        # El campo 'evidencia' es opcional y no está en tu HTML, por lo que es None.
        evidencia = request.form.get("evidencia") if request.form.get("evidencia") else None
        
        id_usuario = session["usuario_id"]

        # 2. Validación de campos obligatorios (Verifica que no sean None ni cadenas vacías)
        if (not tipo_desastre or tipo_desastre.strip() == "") or \
           (not fecha_desastre_str or fecha_desastre_str.strip() == "") or \
           (not direccion_afectada or direccion_afectada.strip() == "") or \
           (not descripcion_danos or descripcion_danos.strip() == ""):
            
            flash("Por favor completa los campos obligatorios marcados (*).", "danger")
            return redirect(url_for("nueva_solicitud")) 

        try:
            # 3. CONVERSIÓN DE FECHA: El input type="date" envía el formato estándar YYYY-MM-DD
            fecha_desastre_obj = datetime.strptime(fecha_desastre_str, '%Y-%m-%d').date()
            
            # 4. CONVERSIÓN DE ENTEROS: 
            personas_afectadas = int(personas_afectadas_str) if personas_afectadas_str and personas_afectadas_str.isdigit() else None

        except ValueError:
            # Este error captura problemas de formato (fecha o número de personas).
            flash("Error en el formato de la fecha o el número de personas. Asegúrate de que las personas afectadas sea un número entero.", "danger")
            return redirect(url_for("nueva_solicitud"))

        # 5. Insertar en la tabla SolicitudAyuda, mapeando los nombres del formulario
        nueva_solicitud = SolicitudAyuda(
            id_usuario=id_usuario,
            descripcion=descripcion_danos, # Mapea 'descripcion_danos' (HTML) a la columna 'descripcion' (BD)
            ubicacion=direccion_afectada, # Mapea 'direccion_afectada' (HTML) a la columna 'ubicacion' (BD)
            evidencia=evidencia,
            tipo_desastre=tipo_desastre,
            fecha_desastre=fecha_desastre_obj, 
            personas_afectadas=personas_afectadas,
            prioridad=prioridad
        )

        db.session.add(nueva_solicitud)
        db.session.commit()

        flash("Solicitud de ayuda enviada exitosamente ✅", "success")
        return redirect(url_for("dashboard"))

    # Si es GET, renderiza el formulario
    return render_template("nueva_solicitud.html")

#======================
#TICKETS SOPORTE
#=======================

#@app.route('/nueva_solicitud', methods=["GET", "POST"])
#def nueva_solicitud():
#    if "usuario_id" not in session:
#        flash("Debes iniciar sesión para crear un solicitud.", "warning")
 #       return redirect(url_for("login"))

#    if request.method == "POST":    
#        asunto = request.form.get("asunto")
#        descripcion = request.form.get("descripcion")
#        id_usuario = session["usuario_id"]

 #       nuevo_ticket = TicketSoporte(
 #           id_usuario=id_usuario,
  #          asunto=asunto,
  #          descripcion=descripcion
 #       )
  #      db.session.add(nuevo_ticket)
  #      db.session.commit()
#
   #     flash("Ticket de soporte creado exitosamente ✅", "success")
     #   return redirect(url_for("dashboard"))
#
 #   return render_template("nueva_solicitud.html")




#============================================================================


# ======================
#   CERRAR SESIÓN
# ======================
@app.route('/logout')
def logout():
    session.clear()
    flash("Sesión cerrada correctamente ✅", "info")
    return redirect(url_for("index"))




@app.route('/perfil')
def perfil():
    return render_template('perfil.html')



# ======================
#   EJECUTAR SERVIDOR
# ======================
if __name__ == '__main__':
    app.run(debug=True)




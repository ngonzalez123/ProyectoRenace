    # models.py
 # Este archivo define la estructura de las tablas de tu base de datos
# usando Flask-SQLAlchemy.

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
import enum

# Inicializa el objeto de base de datos. 
# Esto se importa como 'db' en app.py.
db = SQLAlchemy()

# ----------------------------------------------------------------------
# 1. Definición de Tipos ENUM (para los campos con opciones fijas)
# ----------------------------------------------------------------------

# ENUM para la tabla 'usuarios'
# ENUM para la tabla 'usuarios' - CORRECCIÓN: Clave y Valor en MAYÚSCULAS
class RolUsuario(enum.Enum):
    USUARIO = 'USUARIO' # Ajustado: Clave y Valor coinciden
    ADMIN = 'ADMIN'     # Ajustado: Clave y Valor coinciden
    SOPORTE = 'Soporte Técnico'

# ENUM para la tabla 'solicitudes_ayuda' - CORRECCIÓN: Valores en MAYÚSCULAS
class EstadoSolicitud(enum.Enum):
    PENDIENTE = 'PENDIENTE'
    EN_PROCESO = 'EN_PROCESO'
    RESUELTO = 'RESUELTO'

# ENUM para la tabla 'tickets_soporte' - CORRECCIÓN: Valores en MAYÚSCULAS
class EstadoTicket(enum.Enum):
    ABIERTO = 'ABIERTO' 
    EN_PROCESO = 'EN_PROCESO'
    CERRADO = 'CERRADO'

class Usuario(UserMixin, db.Model): # AÑADIDO: UserMixin
    # Mapea a la tabla 'usuarios' en la base de datos
    __tablename__ = 'usuarios'

    # Columnas
    id_usuario = db.Column(db.Integer, primary_key=True)
    cedula = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(50), nullable=False)
    apellido = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    direccion = db.Column(db.String(255), nullable=False)
    municipio = db.Column(db.String(100), nullable=False, default='Caucasia')
    password = db.Column(db.String(255), nullable=False)

    # Campo ENUM: Usa el Enum RolUsuario con el valor por defecto USUARIO
    rol = db.Column(db.Enum(RolUsuario), default=RolUsuario.USUARIO) 
    
    # TIMESTAMP 
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones: permiten acceder a los datos relacionados (útil en Flask)
    solicitudes = db.relationship('SolicitudAyuda', backref='creador', lazy=True)
    tickets = db.relationship('TicketSoporte', backref='creador_ticket', lazy=True)
    respuestas = db.relationship('Respuesta', backref='autor_respuesta', lazy=True)
    
    # MÉTODO REQUERIDO POR FLASK-LOGIN
    # Este método es usado por load_user, pero se requiere para la compatibilidad con UserMixin
    def get_id(self):
        # Debe devolver el ID del usuario como string
        return str(self.id_usuario)

    # Atributo opcional para usar en la interfaz
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"

class SolicitudAyuda(db.Model):
    __tablename__ = 'solicitudes_ayuda'

    id_solicitud = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    tipo_desastre = db.Column(db.String(100), nullable=False)
    fecha_desastre = db.Column(db.Date, nullable=False)
    personas_afectadas = db.Column(db.Integer)
    prioridad = db.Column(db.String(50))
    descripcion = db.Column(db.Text, nullable=False)
    ubicacion = db.Column(db.String(255), nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)  # ✅ AÑADE ESTA LÍNEA
    estado = db.Column(db.Enum(EstadoSolicitud), default=EstadoSolicitud.PENDIENTE)


class TicketSoporte(db.Model):
    __tablename__ = 'tickets_soporte'

    id_ticket = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    asunto = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    
    # Clave foránea correcta a 'solicitudes_ayuda'
    id_solicitud = db.Column(db.Integer, db.ForeignKey('solicitudes_ayuda.id_solicitud'), nullable=True) 
    
    # Apuntamos al nombre de la clase de modelo 'SolicitudAyuda'
    solicitud_origen = db.relationship('SolicitudAyuda', backref='tickets_soporte_asociados')
    
    # Usamos la clase Enum de Python
    estado = db.Column(db.Enum(EstadoTicket), default=EstadoTicket.ABIERTO) 
    
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relación con las respuestas (comentarios)
    respuestas = db.relationship('Respuesta', backref='ticket_asociado', lazy=True)
    
    def __repr__(self):
        return f"<TicketSoporte {self.id_ticket} - {self.asunto}>"

class Respuesta(db.Model):
    __tablename__ = 'respuestas'

    id_respuesta = db.Column(db.Integer, primary_key=True)
    
    # Claves Foráneas
    id_ticket = db.Column(db.Integer, db.ForeignKey('tickets_soporte.id_ticket'), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    
    mensaje = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

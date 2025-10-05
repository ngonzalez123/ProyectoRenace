# models.py
# Este archivo define la estructura de las tablas de tu base de datos
# usando Flask-SQLAlchemy.

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import enum

# Inicializa el objeto de base de datos. 
# Esto se importa como 'db' en app.py.
db = SQLAlchemy()

# ----------------------------------------------------------------------
# 1. Definición de Tipos ENUM (para los campos con opciones fijas)
# ----------------------------------------------------------------------

# ENUM para la tabla 'usuarios'
class RolUsuario(enum.Enum):
    USUARIO = 'usuario'
    ADMIN = 'admin'

# ENUM para la tabla 'solicitudes_ayuda'
class EstadoSolicitud(enum.Enum):
    PENDIENTE = 'pendiente'
    EN_PROCESO = 'en_proceso'
    RESUELTO = 'resuelto'

# ENUM para la tabla 'tickets_soporte'
class EstadoTicket(enum.Enum):
    ABIERTO = 'Abierto'
    EN_PROCESO = 'En proceso'
    CERRADO = 'Cerrado'

# ----------------------------------------------------------------------
# 2. Clases de Modelos (Mapeo de Tablas)
# ----------------------------------------------------------------------

class Usuario(db.Model):
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
    
    # Campo ENUM
    #rol = db.Column(db.Enum(RolUsuario), default=RolUsuario.USUARIO)
    rol = db.Column(db.Enum('usuario', 'admin'), default='usuario') 
    # TIMESTAMP (usa datetime.utcnow en lugar de current_timestamp para compatibilidad)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones: permiten acceder a los datos relacionados (útil en Flask)
    solicitudes = db.relationship('SolicitudAyuda', backref='creador', lazy=True)
    tickets = db.relationship('TicketSoporte', backref='creador_ticket', lazy=True)
    respuestas = db.relationship('Respuesta', backref='autor_respuesta', lazy=True)


class SolicitudAyuda(db.Model):
    __tablename__ = 'solicitudes_ayuda'

    id_solicitud = db.Column(db.Integer, primary_key=True)
    
    # Clave Foránea: referencia a la tabla 'usuarios'
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    tipo_desastre = db.Column(db.String(100), nullable=False) # Columna 1 de 4
    fecha_desastre = db.Column(db.Date, nullable=False)        # Columna 2 de 4 (Asumimos formato Date)
    personas_afectadas = db.Column(db.Integer)                 # Columna 3 de 4 (Asumimos Integer)
    prioridad = db.Column(db.String(50))     
    descripcion = db.Column(db.Text, nullable=False)    
    ubicacion = db.Column(db.String(255), nullable=True)
    #evidencia = db.Column(db.String(255), nullable=True)
    
    # Campo ENUM
    estado = db.Column(db.Enum(EstadoSolicitud), default=EstadoSolicitud.PENDIENTE)


class TicketSoporte(db.Model):
    __tablename__ = 'tickets_soporte'

    id_ticket = db.Column(db.Integer, primary_key=True)
    
    # Clave Foránea: referencia a la tabla 'usuarios'
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    
    asunto = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Campo ENUM
    estado = db.Column(db.Enum(EstadoTicket), default=EstadoTicket.ABIERTO)

    # Relación: Permite acceder a las respuestas de este ticket
    respuestas = db.relationship('Respuesta', backref='ticket_asociado', lazy=True)


class Respuesta(db.Model):
    __tablename__ = 'respuestas'

    id_respuesta = db.Column(db.Integer, primary_key=True)
    
    # Claves Foráneas
    id_ticket = db.Column(db.Integer, db.ForeignKey('tickets_soporte.id_ticket'), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    
    mensaje = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
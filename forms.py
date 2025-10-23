from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length

# Formulario usado para responder tickets
class ResponderForm(FlaskForm):
    # El campo 'mensaje' debe coincidir con el usado en ver_ticket.html
    mensaje = TextAreaField('Mensaje de Respuesta', validators=[
        DataRequired(message="El mensaje no puede estar vacío."),
        Length(min=5, max=500, message="El mensaje debe tener entre 5 y 500 caracteres.")
    ])
    submit = SubmitField('Enviar Respuesta')
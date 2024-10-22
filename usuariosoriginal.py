import os
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, flash
from tensorflow.keras.models import load_model
from PIL import Image
import psycopg2
from psycopg2 import sql

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Cambia esto por una clave secreta real

# Configuración de la base de datos
PGUSER = 'usuario_uva'
PGHOST = 'localhost'
PGDATABASE = 'proyect_uva'
PGPASSWORD = 'uva12345'
PGPORT = 5432

# Cargar el modelo
modelo = load_model('grape_disease_model5.h5')

# Diccionario de nombres de clases
class_names = {
    0: 'Botrytis cinerea',
    1: 'Esca',
    2: 'Mildiú',
    3: 'Oídio',
    4: 'Podredumbre negra',
    5: 'Saludable',
    6: 'Tizón de la hoja'
}

def process_image(img_path):
    img = Image.open(img_path)
    img = img.resize((224, 224))
    
    img_array = np.array(img)
    
    if img_array.shape[-1] == 4:  # Si tiene 4 canales (RGBA)
        img_array = img_array[..., :3]  # Convertir a RGB
    
    img_array = img_array / 255.0  # Normalizar
    img_array = np.expand_dims(img_array, axis=0)  # Añadir dimensión de batch
    
    predictions = modelo.predict(img_array)
    class_idx = np.argmax(predictions)
    
    return class_names[class_idx], predictions[0][class_idx]

    

# Conectar a la base de datos
def get_db_connection():
    conn = psycopg2.connect(
        dbname=PGDATABASE,
        user=PGUSER,
        password=PGPASSWORD,
        host=PGHOST,
        port=PGPORT
    )
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        contraseña = request.form['contraseña']
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Verificar si el correo ya existe
            cursor.execute("SELECT * FROM usuarios WHERE correo = %s", (correo,))
            existing_user = cursor.fetchone()

            if existing_user:
                flash('El correo electrónico ya está registrado.', 'danger')
                return redirect(url_for('registro'))

            # Si el correo no existe, registrar el nuevo usuario
            cursor.execute(sql.SQL("INSERT INTO usuarios (nombre, correo, contraseña) VALUES (%s, %s, %s)"),
                           [nombre, correo, contraseña])
            conn.commit()
            flash('Registro exitoso', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            print("Error al registrar el usuario:", e)
            flash('Error al registrar el usuario', 'danger')
        finally:
            cursor.close()
            conn.close()
        
    return render_template('registro.html')


@app.route('/ingresar', methods=['GET', 'POST'])
def ingresar():
    if request.method == 'POST':
        correo = request.form['correo']
        contraseña = request.form['contraseña']
        
        # Conectar a la base de datos y verificar las credenciales
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE correo = %s AND contraseña = %s", (correo, contraseña))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('imagenes'))  # Redirige a la página de imágenes
        else:
            flash('Correo o contraseña incorrectos', 'danger')
            return redirect(url_for('ingresar'))  # Regresa a la página de inicio de sesión

    return render_template('ingresar.html')

@app.route('/imagenes', methods=["GET", "POST"])
def imagenes():
    if request.method == "POST":
        file = request.files.get('image')
        if file:
            img_path = os.path.join('static', file.filename)
            file.save(img_path)
            class_name, probability = process_image(img_path)
            return render_template("imagenes.html", class_name=class_name, probability=probability, img_path=img_path)
    return render_template("imagenes.html")

if __name__ == '__main__':
    app.run(debug=True)

import os
import numpy as np
import cv2
from flask import Flask, render_template, request, redirect, url_for, flash, session  # Asegúrate de tener 'session' importado
from tensorflow.keras.models import load_model  # type: ignore
from PIL import Image
import psycopg2
from psycopg2 import sql
import json  # Para guardar los datos en JSON

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

def process_video(video_path):
    cap = cv2.VideoCapture(video_path)
    frame_rate = int(cap.get(cv2.CAP_PROP_FPS))
    frame_interval = 10
    frame_count = 0
    processed_frames = []
    detected_classes = []

    first_detected_class = None
    last_frame = None  # Para almacenar el último frame

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_interval == 0:
            frame_resized = cv2.resize(frame, (224, 224))
            img_array = np.array(frame_resized) / 255.0
            img_array = np.expand_dims(img_array, axis=0)

            predictions = modelo.predict(img_array)

            if predictions is not None and len(predictions) > 0:
                class_idx = np.argmax(predictions)
                class_name = class_names.get(class_idx, "Desconocida")
                probability = predictions[0][class_idx]

                if probability >= 0.2:
                    if not first_detected_class:
                        first_detected_class = class_name
                        print(f"Primera clase detectada: {first_detected_class}")

                    processed_frames.append({
                        'frame': frame_count,
                        'class_name': class_name
                    })
                    detected_classes.append(class_name)
                    print(f"Frame: {frame_count}, Clase: {class_name}")

                else:
                    processed_frames.append({
                        'frame': frame_count,
                        'class_name': first_detected_class if first_detected_class else "No detectada"
                    })

            else:
                processed_frames.append({
                    'frame': frame_count,
                    'class_name': first_detected_class if first_detected_class else "No detectada"
                })

            last_frame = frame  # Almacena el último frame procesado

        frame_count += 1

    cap.release()

    # Procesar el último frame
    if last_frame is not None:
        last_frame_path = os.path.join('static', 'last_frame.png')
        cv2.imwrite(last_frame_path, last_frame)  # Guarda el último frame

    if detected_classes:
        first_detected_class = max(set(detected_classes), key=detected_classes.count)
    else:
        first_detected_class = "No detectada"

    return processed_frames, first_detected_class, last_frame_path if last_frame is not None else None

def save_frames_to_file(processed_frames):
    # Guardar los frames procesados en un archivo JSON
    with open('frames_data.json', 'w') as f:
        json.dump(processed_frames, f)

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
            session['user_id'] = user[0]  # Guarda el ID del usuario en la sesión
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('imagenes'))  # Redirige a la página de imágenes
        else:
            flash('Correo o contraseña incorrectos', 'danger')
            return redirect(url_for('ingresar'))  # Regresa a la página de inicio de sesión

    return render_template('ingresar.html')

@app.route('/imagenes', methods=["GET", "POST"])
def imagenes():
    if 'user_id' not in session:
        flash('Por favor, inicia sesión primero', 'danger')
        return redirect(url_for('ingresar'))

    if request.method == "POST":
        file = request.files.get('media')  # Cambia 'image' o 'video' a 'media'
        if file:
            file_type = file.content_type  # Detectar el tipo de archivo (imagen o video)
            
            # Definir la ruta de guardado
            file_path = os.path.join('static', file.filename)
            file.save(file_path)
            
            if "image" in file_type:
                class_name, probability = process_image(file_path)  # Procesar la imagen
                media_type = 'image'
                frames_result = None
            elif "video" in file_type:
                frames_result, first_detected_class, last_frame_path = process_video(file_path)  # Procesar el video
                media_type = 'video'
                save_frames_to_file(frames_result)  # Guarda los frames en un archivo JSON
            else:
                flash("Tipo de archivo no soportado", "danger")
                return redirect(url_for("imagenes"))
            
            return render_template("imagenes.html", 
                                   media_type=media_type, 
                                   class_name=class_name if media_type == 'image' else None, 
                                   frames_result=frames_result if media_type == 'video' else None, 
                                   first_detected_class=first_detected_class if media_type == 'video' else None,
                                   last_frame_path=last_frame_path if media_type == 'video' else None,
                                   media_path=file_path)
    return render_template("imagenes.html")

@app.route('/logout')
def logout():
    session.clear()  # Elimina toda la sesión del usuario
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('index'))  # Redirige a la página de inicio (index)

@app.route('/video', methods=["GET", "POST"])
def video():
    if request.method == "POST":
        file = request.files.get('video')
        if file:
            video_path = os.path.join('static', file.filename)
            file.save(video_path)

            # Procesar el video
            frames_result, first_detected_class, last_frame_path = process_video(video_path)
            save_frames_to_file(frames_result)  # Guarda los frames en un archivo JSON

            return render_template("imagenes.html", 
                                   frames_result=frames_result, 
                                   video_path=video_path, 
                                   first_detected_class=first_detected_class,
                                   last_frame_path=last_frame_path)  # Añadido last_frame_path

    return render_template("imagenes.html")

if __name__ == '__main__':
    app.run(debug=True)

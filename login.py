from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Cambia esto por una clave secreta real

# Conectar a la base de datos
def get_db_connection():
    conn = psycopg2.connect(
        dbname='proyect_uva',
        user='usuario_uva',
        password='uva12345',
        host='localhost',
        port='5432'
    )
    return conn

@app.route('/ingresar', methods=['GET', 'POST'])
def ingresar():
    if request.method == 'POST':
        correo = request.form['correo']
        contraseña = request.form['contraseña']
        
        # Conectar a la base de datos y verificar las credenciales
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM usuarios WHERE correo = %s AND contraseña = %s", (correo, contraseña))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('imagenes'))  # Cambia aquí para redirigir a imágenes.html
        else:
            flash('Correo o contraseña incorrectos', 'danger')
            return redirect(url_for('ingresar'))  # Regresa a la página de inicio de sesión

    return render_template('ingresar.html')

@app.route('/imagenes')
def imagenes():
    return render_template('imagenes.html')  # Asegúrate de tener este archivo en templates

@app.route('/')
def index():
    return render_template('index.html')  # Asegúrate de tener este archivo en templates

if __name__ == '__main__':
    app.run(debug=True)

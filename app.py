from flask import Flask, request, jsonify, render_template_string
import schedule
import time
import threading
import requests
import json
import os

app = Flask(__name__)

# Archivo para almacenar enlaces y contenido actualizado
DATA_FILE = 'm3u_data.json'

# Función para cargar datos
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {'links': [], 'updated_content': {}}

# Función para guardar datos
def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

# Función para actualizar enlaces cada 5 minutos
def update_links():
    data = load_data()
    for link in data['links']:
        try:
            response = requests.get(link, timeout=10)
            if response.status_code == 200:
                data['updated_content'][link] = response.text
                print(f"Actualizado: {link}")
            else:
                print(f"Error en {link}: {response.status_code}")
        except Exception as e:
            print(f"Error descargando {link}: {e}")
    save_data(data)

# Iniciar el scheduler en un hilo separado
def run_scheduler():
    schedule.every(5).minutes.do(update_links)
    while True:
        schedule.run_pending()
        time.sleep(1)

# Página principal (frontend simple)
@app.route('/')
def index():
    data = load_data()
    html = """
    <h1>Gestor de Enlaces M3U</h1>
    <form action="/add" method="post">
        <input type="text" name="url" placeholder="Ingresa URL M3U" required>
        <button type="submit">Agregar</button>
    </form>
    <h2>Enlaces Agregados:</h2>
    <ul>
    {% for link in data.links %}
        <li>{{ link }}</li>
    {% endfor %}
    </ul>
    <h2>Enlace de Playlist General:</h2>
    <a href="/playlist.m3u">Descargar Playlist Combinada</a>
    """
    return render_template_string(html, data=data)

# Agregar enlace
@app.route('/add', methods=['POST'])
def add_link():
    url = request.form['url']
    data = load_data()
    if url not in data['links']:
        data['links'].append(url)
        save_data(data)
        update_links()  # Actualizar inmediatamente
    return jsonify({'message': 'Enlace agregado'})

# Generar M3U combinada
@app.route('/playlist.m3u')
def generate_playlist():
    data = load_data()
    combined = "#EXTM3U\n"
    for content in data['updated_content'].values():
        # Asumir que cada M3U tiene líneas como #EXTINF y URLs
        lines = content.split('\n')
        for line in lines:
            if line.startswith('#EXTINF') or line.startswith('http'):
                combined += line + '\n'
    return combined, {'Content-Type': 'application/x-mpegurl'}

if __name__ == '__main__':
    # Cargar datos iniciales
    data = load_data()
    save_data(data)
    
    # Iniciar scheduler en hilo
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    app.run(debug=True)

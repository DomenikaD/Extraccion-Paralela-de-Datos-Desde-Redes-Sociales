import os
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from scraper import ConcurrentScraper

PORT = 8000
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Sobrescribir para registrar las peticiones en la consola
        super().log_message(format, *args)
        
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        # Endpoints de la API
        if path == '/api/extract':
            query = query_params.get('q', [''])[0]
            if not query:
                self.send_error_response(400, "Falta el parámetro de búsqueda 'q'")
                return
                
            limit = int(query_params.get('limit', ['15'])[0])
            
            # Ejecutar el raspador concurrente
            scraper = ConcurrentScraper(query, limit_per_source=limit)
            report = scraper.execute_parallel()
            
            self.send_json_response(200, report)
            return
            
        elif path == '/api/dataset':
            json_path = os.path.join(DATA_DIR, 'dataset.json')
            if not os.path.exists(json_path):
                self.send_json_response(200, [])
                return
                
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.send_json_response(200, data)
            except Exception as e:
                self.send_error_response(500, f"Error al cargar dataset: {str(e)}")
            return



        # Servir archivos estáticos del frontend
        if path == '/':
            path = '/index.html'
            
        # Normalizar y prevenir vulnerabilidad de Directory Traversal
        local_path = os.path.abspath(os.path.join(WEB_DIR, path.lstrip('/')))
        if not local_path.startswith(os.path.abspath(WEB_DIR)):
            self.send_error_response(403, "Acceso denegado")
            return
            
        if not os.path.exists(local_path) or os.path.isdir(local_path):
            self.send_error_response(404, f"Archivo no encontrado: {path}")
            return
            
        # Determinar el Content-Type adecuado
        content_type = 'text/html; charset=utf-8'
        if local_path.endswith('.css'):
            content_type = 'text/css; charset=utf-8'
        elif local_path.endswith('.js'):
            content_type = 'application/javascript; charset=utf-8'
        elif local_path.endswith('.json'):
            content_type = 'application/json; charset=utf-8'
        elif local_path.endswith('.png'):
            content_type = 'image/png'
        elif local_path.endswith('.jpg') or local_path.endswith('.jpeg'):
            content_type = 'image/jpeg'
        elif local_path.endswith('.svg'):
            content_type = 'image/svg+xml'
            
        self.send_file_response(local_path, content_type)

    def send_json_response(self, status, data):
        response_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response_bytes)

    def send_error_response(self, status, message):
        response_bytes = json.dumps({"error": message}, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def send_file_response(self, filepath, content_type, download=False, filename=None):
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            if download:
                fn = filename or os.path.basename(filepath)
                self.send_header('Content-Disposition', f'attachment; filename="{fn}"')
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error_response(500, f"Error al leer archivo: {str(e)}")

def run_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, DashboardHandler)
    print(f"===========================================================")
    print(f" Servidor iniciado en http://localhost:{PORT}")
    print(f" Abre esta URL en tu navegador para ver el Dashboard")
    print(f" Presiona Ctrl+C en la terminal para detener el servidor")
    print(f"===========================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nDeteniendo servidor...")
        httpd.server_close()
        print("Servidor detenido exitosamente.")

if __name__ == '__main__':
    # Asegurar que el directorio web existe
    os.makedirs(WEB_DIR, exist_ok=True)
    run_server()

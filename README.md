# Práctica de Laboratorio 06
## Desarrollo e implementación de aplicaciones de cómputo paralelo para extracción concurrente de datos desde redes sociales

### Universidad Politécnica Salesiana
**Carrera:** Ingeniería en Ciencias de la Computación

**Asignatura:** Computación Paralela

**Estudiantes:** Domenika Delgado, Robinson Redrovan, David Uzhca

---

# Descripción

Este proyecto implementa un sistema concurrente de extracción, sincronización y almacenamiento de opiniones en plataformas digitales utilizando Computación Paralela.

El sistema se enfoca en analizar debates y percepciones sobre la problemática seleccionada:

> Opiniones y percepciones sobre el uso de la Inteligencia Artificial (IA) en la educación.

Se realiza la extracción concurrente en tiempo real desde tres fuentes digitales altamente diferenciadas:

- Reddit
- Hacker News
- GitHub (Issues)

El procesamiento de los flujos de red se realiza utilizando múltiples hilos mediante la librería **concurrent.futures** y colas sincronizadas con **queue.Queue** de Python, garantizando un almacenamiento ordenado libre de condiciones de carrera (Race Conditions).

---

# Objetivos

- Identificar una problemática real (uso de IA en la educación).
- Diseñar una estrategia de extracción de datos basada en consultas por palabras clave.
- Seleccionar tres fuentes digitales (Reddit, Hacker News, GitHub) relacionadas con la problemática.
- Implementar una solución paralela o concurrente en Python para extraer datos de las tres fuentes de forma simultánea.
- Aplicar y justificar los conceptos de computación paralela revisados en la asignatura (hilos, colas thread-safe y patrón Productor-Consumidor).
- Generar una base inicial de datos textuales en formatos CSV y JSON conservando la trazabilidad.

---

# Tecnologías utilizadas

- Python 3.12
- Requests (Peticiones HTTP a las APIs oficiales/públicas)
- concurrent.futures (ThreadPoolExecutor para concurrencia I/O-Bound)
- queue.Queue (Cola sincronizada thread-safe)
- HTML5 / CSS3 / JavaScript (Dashboard web de visualización en tiempo real)

---

# Estructura del proyecto

```
Practica06/
│
├── data/
│   ├── dataset.csv
│   └── dataset.json
│
├── web/
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   ├── reddit.png
│   ├── hackernews.png
│   └── github.png
│
├── app.py
├── scraper.py
└── README.md
```

---

# Estrategia de búsqueda y filtros

Se emplean endpoints públicos de búsqueda que no requieren llaves de API o autenticación:

- **Reddit Search API:** Peticiones HTTP a `reddit.com/search.json` y fallback de respaldo a PullPush.
- **Hacker News Algolia API:** Búsqueda en `hn.algolia.com` traduciendo automáticamente los términos clave al inglés para asegurar la obtención de hilos reales.
- **GitHub Issues API:** Búsqueda de incidencias técnicas en `api.github.com/search/issues`.

Se aplica un filtro estricto por tokens de coincidencia temática que analiza la combinación de **Título + Cuerpo** de cada publicación, exigiendo la presencia de al menos un término clave de IA (*ia, ai, chatgpt, etc.*) y educación (*estudiante, profesor, etc.*). Asimismo, se filtran subreddits baneados o spam conocidos (como `geekeducativo.com`).

---

# Técnica de paralelismo utilizada

Para cumplir con el requerimiento principal de paralelismo de la práctica, se implementó el patrón **Productor-Consumidor**:

- **ThreadPoolExecutor:** Dado que la extracción consiste en llamadas a servidores remotos (operación **I/O-Bound**), se disparan 3 hilos productores concurrentes que realizan las peticiones de red simultáneamente.
- **queue.Queue:** Actúa como el buffer de sincronización seguro entre hilos (thread-safe). Cada hilo productor deposita de forma asíncrona sus registros extraídos en la cola.
- **Hilo Consumidor (Escritor):** Un hilo en segundo plano lee secuencialmente de la cola y realiza la escritura atómica en el disco para evitar colisiones en la creación del dataset.

---

# Flujo del sistema

```
            Interfaz Web (Dashboard)
                       │
                       ▼
            Controlador Local (app.py)
                       │
                       ▼
            ThreadPoolExecutor (scraper.py)
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
      Hilo 1        Hilo 2        Hilo 3
      Reddit     Hacker News      GitHub
     (APIs)     (Algolia API)  (Issues API)
         │             │             │
         └───────────┬─┴─────────────┘
                     ▼ (Asíncrono / put)
               queue.Queue (Cola Segura)
                     │
                     ▼ (Sincronizado / get)
               Hilo Consumidor (Escritor)
         ┌───────────┴───────────┐
         ▼                       ▼
    dataset.csv             dataset.json
```

---

# Instalación

### Paso 1: Clonar o abrir el directorio del proyecto
Abre tu consola o terminal en la carpeta principal `Practica06/`.

### Paso 2: Crear el entorno virtual (venv)
*   **Linux / macOS:**
    ```bash
    python3 -m venv venv
    ```
*   **Windows:**
    ```powershell
    python -m venv venv
    ```

### Paso 3: Activar el entorno virtual
*   **Linux / macOS:**
    ```bash
    source venv/bin/activate
    ```
*   **Windows (PowerShell):**
    ```powershell
    .\venv\Scripts\Activate.ps1
    ```
*   **Windows (Símbolo del sistema / CMD):**
    ```cmd
    venv\Scripts\activate.bat
    ```

### Paso 4: Instalar dependencias
Instala la librería `requests` necesaria para las peticiones HTTP:
```bash
pip install requests
```

---

# Ejecución

### Paso 1: Ejecutar el servidor web local
Inicia la aplicación ejecutando:
```bash
python app.py
```

### Paso 2: Acceder al Dashboard
Abre tu navegador web e ingresa a:
[http://localhost:8000](http://localhost:8000)

### Paso 3: Extraer datos en paralelo
Escribe tus palabras clave, selecciona el límite de registros y haz clic en **"Buscar"**.

---

# Salida

El programa consolida la información extraída y genera en la carpeta `data/`:

- `data/dataset.json`
- `data/dataset.csv`

Cada registro guardado mantiene la trazabilidad mediante las columnas:
- `source`: Red social de origen (Reddit, Hacker News o GitHub).
- `query`: Palabra clave de búsqueda.
- `title`: Título de la publicación o incidencia.
- `text`: Texto descriptivo original.
- `author`: Nombre de usuario del creador.
- `date`: Fecha y hora de publicación (`AAAA-MM-DD HH:MM:SS`).
- `url`: Enlace real en vivo para la verificación del origen.
- `metrics`: Diccionario JSON de interacciones reales (votos, puntos, comentarios).

---

# Evidencia de ejecución

Durante la extracción, las tarjetas muestran el estado concurrente en tiempo real. En la consola se muestra el log de extracción multihilo exitosa:

```
=== Iniciando Extracción Concurrente de Prueba (Consola) ===

--- Estado de las fuentes ---
[Reddit] Estado: Completado | Cantidad: 5 | Origen: Real (Reddit API)
[Hacker News] Estado: Completado | Cantidad: 5 | Origen: Real (Algolia API)
[GitHub] Estado: Completado | Cantidad: 5 | Origen: Real (GitHub API)

Tiempo Total Concurrente: 5.67 segundos
Total registros guardados en data/: 15
```

---
# Extraccion-Paralela-de-Datos-Desde-Redes-Sociales

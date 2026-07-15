import os
import csv
import json
import time
import queue
import random
import re
import urllib.parse
from datetime import datetime
import concurrent.futures
import requests

# Configuración y directorios
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

CSV_FILE = os.path.join(DATA_DIR, 'dataset.csv')
JSON_FILE = os.path.join(DATA_DIR, 'dataset.json')

# Lista de User-Agents para emular peticiones del navegador
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
]


class ConcurrentScraper:
    def __init__(self, query, limit_per_source=15):
        self.query = query
        self.limit = limit_per_source
        self.data_queue = queue.Queue()
        self.results = []
        self.status = {
            "Reddit": {"status": "Pendiente", "count": 0, "type": "Ninguno"},
            "Hacker News": {"status": "Pendiente", "count": 0, "type": "Ninguno"},
            "GitHub": {"status": "Pendiente", "count": 0, "type": "Ninguno"}
        }
        self.start_time = None
        self.end_time = None

    def _get_search_queries(self):
        """Genera consultas equivalentes en inglés si la búsqueda es en español para asegurar resultados reales."""
        q = self.query.lower()
        queries = [self.query]
        
        has_spanish = any(w in q for w in ["inteligencia", "artificial", "educacion", "educación", "estudiante", "estudiantes", "profesor", "profesores", "escuela", "colegio", "universidad", "estudios", "ia"])
        if has_spanish:
            eng_q = self.query
            eng_q = eng_q.replace("inteligencia artificial", "artificial intelligence")
            eng_q = eng_q.replace("inteligencia", "intelligence")
            eng_q = eng_q.replace("artificial", "artificial")
            eng_q = eng_q.replace("educacion", "education").replace("educación", "education")
            eng_q = eng_q.replace("estudiante", "student").replace("estudiantes", "students")
            eng_q = eng_q.replace("profesor", "teacher").replace("profesores", "teachers")
            eng_q = eng_q.replace("escuela", "school").replace("escuelas", "schools")
            eng_q = eng_q.replace("estudios", "education")
            eng_q = eng_q.replace("ia", "ai")
            if eng_q.lower() != self.query.lower():
                queries.append(eng_q)
                
        return queries

    def _has_strict_topic_match(self, title, text):
        """Verifica que el post hable de IA y Educación combinando título y texto."""
        combined_text = (title + " " + text).lower()
        tokens = set(re.findall(r'\b\w+\b', combined_text))
        
        # Palabras clave del mundo IA
        ai_keywords = {"ia", "ai", "chatgpt", "gemini", "copilot", "llm", "openai", "claude", "artificial", "inteligencia"}
        # Palabras clave del mundo Educación
        edu_keywords = {
            "educacion", "educación", "estudiante", "estudiantes", "profesor", "profesores", 
            "docente", "docentes", "clase", "clases", "escuela", "escuelas", "colegio", 
            "colegios", "universidad", "universidades", "aula", "aulas", "enseñanza", 
            "tutor", "tutores", "tarea", "tareas", "estudiar", "estudios",
            "education", "student", "students", "teacher", "teachers", "learning", "college", 
            "school", "classroom", "classrooms", "pedagogy", "class", "classes", "study", "studying",
            "homework", "essay", "essays", "exam", "exams", "test", "tests", "grading", "grade", "grades",
            "teaching", "teach", "course", "courses", "curriculum", "academia", "academic", "educator", "educators"
        }
        
        has_ai = any(w in tokens for w in ai_keywords)
        has_edu = any(w in tokens for w in edu_keywords)
        
        return has_ai and has_edu

    def scrape_reddit(self):
        """Extrae datos reales de Reddit usando su API JSON oficial de búsqueda y PullPush como backup."""
        source_name = "Reddit"
        self.status[source_name]["status"] = "Extrayendo..."
        
        queries = self._get_search_queries()
        count = 0
        
        for q_term in queries:
            if count >= self.limit:
                break
                
            encoded_query = urllib.parse.quote(q_term)
            url = f"https://www.reddit.com/search.json?q={encoded_query}&limit=50"
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            
            try:
                time.sleep(random.uniform(0.5, 1.0))
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    children = data.get("data", {}).get("children", [])
                    
                    for child in children:
                        post_data = child.get("data", {})
                        title_str = post_data.get("title", "")
                        text_str = post_data.get("selftext", "") or ""
                        subreddit_str = post_data.get("subreddit", "")
                        
                        # Filtro estricto del tema
                        if not self._has_strict_topic_match(title_str, text_str):
                            continue
                            
                        # Evitar subreddits o dominios baneados/spam conocidos
                        if text_str.strip() in ("[removed]", "[deleted]"):
                            continue
                        if "geekeducativo" in title_str.lower() or "geekeducativo" in text_str.lower() or "geekeducativo" in subreddit_str.lower():
                            continue
                            
                        created_utc = post_data.get("created_utc", time.time())
                        date_str = datetime.fromtimestamp(created_utc).strftime('%Y-%m-%d %H:%M:%S')
                        
                        permalink = post_data.get("permalink", "")
                        post_url = f"https://www.reddit.com{permalink}" if permalink else f"https://www.reddit.com/search/?q={encoded_query}"
                        
                        record = {
                            "source": source_name,
                            "query": self.query,
                            "title": title_str,
                            "text": text_str[:800] or title_str,
                            "author": f"u/{post_data.get('author', 'anonimo')}",
                            "date": date_str,
                            "url": post_url,
                            "metrics": json.dumps({
                                "upvotes": post_data.get("score", 0),
                                "comments": post_data.get("num_comments", 0)
                            })
                        }
                        self.data_queue.put(record)
                        count += 1
                        if count >= self.limit:
                            break
                else:
                    raise Exception(f"HTTP {response.status_code}")
            except Exception:
                # Fallback secundario a PullPush
                pullpush_url = f"https://api.pullpush.io/reddit/search/submission/?q={encoded_query}&size=50"
                try:
                    response = requests.get(pullpush_url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        posts = data.get("data", [])
                        for post_data in posts:
                            title_str = post_data.get("title", "")
                            text_str = post_data.get("selftext", "") or ""
                            subreddit_str = post_data.get("subreddit", "")
                            
                            if not self._has_strict_topic_match(title_str, text_str):
                                continue
                                
                            if text_str.strip() in ("[removed]", "[deleted]"):
                                continue
                            if "geekeducativo" in title_str.lower() or "geekeducativo" in text_str.lower() or "geekeducativo" in subreddit_str.lower():
                                continue
                                
                            created_utc = post_data.get("created_utc", time.time())
                            date_str = datetime.fromtimestamp(created_utc).strftime('%Y-%m-%d %H:%M:%S')
                            
                            permalink = post_data.get("permalink", "")
                            post_url = f"https://www.reddit.com{permalink}" if permalink else f"https://www.reddit.com/search/?q={encoded_query}"
                            
                            record = {
                                "source": source_name,
                                "query": self.query,
                                "title": title_str,
                                "text": text_str[:800] or title_str,
                                "author": f"u/{post_data.get('author', 'anonimo')}",
                                "date": date_str,
                                "url": post_url,
                                "metrics": json.dumps({
                                    "upvotes": post_data.get("score", 0),
                                    "comments": post_data.get("num_comments", 0)
                                })
                            }
                            self.data_queue.put(record)
                            count += 1
                            if count >= self.limit:
                                break
                except Exception:
                    pass

        self.status[source_name]["status"] = "Completado"
        self.status[source_name]["count"] = count
        self.status[source_name]["type"] = "Real (Reddit API)"

    def scrape_hackernews(self):
        """Extrae datos reales de Hacker News usando la API pública de Algolia."""
        source_name = "Hacker News"
        self.status[source_name]["status"] = "Extrayendo..."
        
        queries = self._get_search_queries()
        count = 0
        
        for q_term in queries:
            if count >= self.limit:
                break
                
            encoded_query = urllib.parse.quote(q_term)
            url = f"https://hn.algolia.com/api/v1/search?query={encoded_query}&tags=story&hitsPerPage=50"
            
            try:
                time.sleep(random.uniform(0.3, 0.8))
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    hits = data.get("hits", [])
                    
                    for hit in hits:
                        title_str = hit.get("title", "")
                        text_str = hit.get("story_text", "") or ""
                        
                        if not self._has_strict_topic_match(title_str, text_str):
                            continue
                            
                        created_at_i = hit.get("created_at_i", int(time.time()))
                        date_str = datetime.fromtimestamp(created_at_i).strftime('%Y-%m-%d %H:%M:%S')
                        
                        object_id = hit.get("objectID", "")
                        post_url = hit.get("url", "")
                        if not post_url and object_id:
                            post_url = f"https://news.ycombinator.com/item?id={object_id}"
                            
                        record = {
                            "source": source_name,
                            "query": self.query,
                            "title": title_str,
                            "text": text_str or title_str,
                            "author": hit.get("author", "anonimo"),
                            "date": date_str,
                            "url": post_url,
                            "metrics": json.dumps({
                                "points": hit.get("points", 0),
                                "comments": hit.get("num_comments", 0)
                            })
                        }
                        self.data_queue.put(record)
                        count += 1
                        if count >= self.limit:
                            break
                else:
                    raise Exception(f"HTTP {response.status_code}")
            except Exception:
                pass

        self.status[source_name]["status"] = "Completado"
        self.status[source_name]["count"] = count
        self.status[source_name]["type"] = "Real (Algolia API)"

    def scrape_github(self):
        """Extrae issues reales de GitHub usando la API de búsqueda pública."""
        source_name = "GitHub"
        self.status[source_name]["status"] = "Extrayendo..."
        
        queries = self._get_search_queries()
        count = 0
        
        for q_term in queries:
            if count >= self.limit:
                break
                
            encoded_query = urllib.parse.quote(q_term)
            url = f"https://api.github.com/search/issues?q={encoded_query}+is:issue&per_page=50"
            headers = {"User-Agent": "Practica06-StudentProject/1.0"}
            
            try:
                time.sleep(random.uniform(0.3, 0.8))
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    
                    for item in items:
                        title_str = item.get("title", "")
                        text_str = item.get("body", "") or ""
                        
                        if not self._has_strict_topic_match(title_str, text_str):
                            continue
                            
                        created_at = item.get("created_at", "")
                        if created_at:
                            date_str = created_at.replace('T', ' ').replace('Z', '')
                        else:
                            date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            
                        post_url = item.get("html_url", f"https://github.com/search?q={encoded_query}&type=issues")
                        author = item.get("user", {}).get("login", "anonimo")
                        
                        record = {
                            "source": source_name,
                            "query": self.query,
                            "title": title_str,
                            "text": text_str[:800] or title_str,
                            "author": author,
                            "date": date_str,
                            "url": post_url,
                            "metrics": json.dumps({
                                "comments": item.get("comments", 0)
                            })
                        }
                        self.data_queue.put(record)
                        count += 1
                        if count >= self.limit:
                            break
                else:
                    raise Exception(f"HTTP {response.status_code}")
            except Exception:
                pass

        self.status[source_name]["status"] = "Completado"
        self.status[source_name]["count"] = count
        self.status[source_name]["type"] = "Real (GitHub API)"

    def run_consumer(self):
        """Hilo Consumidor que extrae elementos de la cola y los consolida."""
        while True:
            try:
                record = self.data_queue.get(timeout=1.0)
                if record is None:
                    break
                self.results.append(record)
                self.data_queue.task_done()
            except queue.Empty:
                continue

    def execute_parallel(self):
        """Ejecuta los extractores en paralelo utilizando ThreadPoolExecutor y la Cola Sincronizada."""
        self.start_time = time.time()
        self.results = []
        
        import threading
        consumer_thread = threading.Thread(target=self.run_consumer)
        consumer_thread.start()
        
        extractors = [self.scrape_reddit, self.scrape_hackernews, self.scrape_github]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(func): func.__name__ for func in extractors}
            concurrent.futures.wait(futures)

        self.data_queue.put(None)
        consumer_thread.join()
        
        self.end_time = time.time()
        self.save_to_files()
        
        return {
            "duration_seconds": round(self.end_time - self.start_time, 2),
            "total_records": len(self.results),
            "status": self.status,
            "results": self.results
        }

    def save_to_files(self):
        """Guarda los resultados a CSV y JSON."""
        if not self.results:
            # Si no hay resultados, limpiar archivos viejos para no mostrar caché basura
            if os.path.exists(JSON_FILE):
                os.remove(JSON_FILE)
            if os.path.exists(CSV_FILE):
                os.remove(CSV_FILE)
            return

        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=4)
            
        fieldnames = ["source", "query", "title", "text", "author", "date", "url", "metrics"]
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in self.results:
                writer.writerow(record)


if __name__ == "__main__":
    print("=== Iniciando Extracción Concurrente de Prueba (Consola) ===")
    query_test = "inteligencia artificial educacion"
    scraper = ConcurrentScraper(query_test, limit_per_source=5)
    
    report = scraper.execute_parallel()
    
    print("\n--- Estado de las fuentes ---")
    for src, details in report["status"].items():
        print(f"[{src}] Estado: {details['status']} | Cantidad: {details['count']} | Origen: {details['type']}")
        
    print(f"\nTiempo Total Concurrente: {report['duration_seconds']} segundos")
    print(f"Total registros guardados en data/: {report['total_records']}")

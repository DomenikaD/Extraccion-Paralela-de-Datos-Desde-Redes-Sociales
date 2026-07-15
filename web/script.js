// Estado Global de la Aplicación
let localDataset = [];
let activeFilter = 'all';
let activeSearchQuery = '';

// Elementos del DOM
const btnStart = document.getElementById('btnStartExtraction');
const queryInput = document.getElementById('searchQuery');
const limitSelect = document.getElementById('limitPerSource');
const tableBody = document.getElementById('tableBody');
const searchInput = document.getElementById('tableSearch');
const filterBtns = document.querySelectorAll('.filter-btn');
const tabBtns = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');


// Tarjetas de Fuentes
const cards = {
    Reddit: document.getElementById('card-reddit'),
    'Hacker News': document.getElementById('card-hackernews'),
    GitHub: document.getElementById('card-github')
};

// Inicialización
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadExistingDataset();
});

// Registrar eventos de la interfaz
function setupEventListeners() {
    // Iniciar Extracción
    btnStart.addEventListener('click', startExtraction);

    // Búsqueda / Filtro en tabla
    searchInput.addEventListener('input', (e) => {
        activeSearchQuery = e.target.value.toLowerCase().trim();
        renderTable();
    });

    // Botones de filtro por Red Social
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            activeFilter = btn.dataset.filter;
            renderTable();
        });
    });

    // Navegación por pestañas (Tabs)
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(btn.dataset.tab).classList.add('active');
        });
    });
}

// Cargar dataset preexistente al iniciar la página
async function loadExistingDataset() {
    try {
        const response = await fetch('/api/dataset');
        if (response.ok) {
            const data = await response.json();
            if (data && data.length > 0) {
                localDataset = data;
                renderTable();
                updateMetrics(data.length, 0.01); // Tiempo ficticio inicial
                
                // Actualizar tarjetas con estado completado
                Object.keys(cards).forEach(source => {
                    const sourceData = data.filter(item => item.source === source);
                    updateCardStatus(source, 'Completado', sourceData.length, 'Cargado');
                });
            }
        }
    } catch (error) {
        console.error('Error al cargar dataset existente:', error);
    }
}

// Ejecutar el scraping concurrente en el backend
async function startExtraction() {
    const query = queryInput.value.trim();
    if (!query) {
        alert('Por favor introduce un criterio de búsqueda.');
        return;
    }

    const limit = limitSelect.value;
    
    // 1. Preparar interfaz (Bloquear controles y animar loaders)
    btnStart.disabled = true;
    queryInput.disabled = true;
    limitSelect.disabled = true;
    searchInput.value = '';
    activeSearchQuery = '';
    
    // Poner todas las tarjetas en estado de carga
    Object.keys(cards).forEach(source => {
        updateCardStatus(source, 'Extrayendo...', 0, 'Ninguno');
    });

    // Iniciar cronómetro visual
    let elapsed = 0.0;
    document.getElementById('metricTime').innerText = '0.00s';
    document.getElementById('metricTotal').innerText = '0';
    document.getElementById('metricSpeed').innerText = '0 /s';
    
    const timerInterval = setInterval(() => {
        elapsed += 0.05;
        document.getElementById('metricTime').innerText = `${elapsed.toFixed(2)}s`;
    }, 50);

    try {
        // 2. Realizar petición HTTP al backend
        const response = await fetch(`/api/extract?q=${encodeURIComponent(query)}&limit=${limit}`);
        
        clearInterval(timerInterval);
        
        if (!response.ok) {
            throw new Error(`Error en servidor: ${response.statusText}`);
        }
        
        const report = await response.json();
        
        // 3. Procesar respuesta y actualizar interfaz
        localDataset = report.results;
        
        // Detener cronómetro y fijar tiempo final real
        document.getElementById('metricTime').innerText = `${report.duration_seconds.toFixed(2)}s`;
        
        // Actualizar estados individuales de las fuentes concurrentes
        Object.keys(cards).forEach(source => {
            const srcStatus = report.status[source];
            if (srcStatus) {
                updateCardStatus(source, srcStatus.status, srcStatus.count, srcStatus.type);
            }
        });

        // Actualizar métricas generales
        updateMetrics(report.total_records, report.duration_seconds);
        
        // Renderizar tabla con nuevos datos
        renderTable();


    } catch (error) {
        clearInterval(timerInterval);
        alert(`Error al realizar la extracción concurrente: ${error.message}`);
        console.error(error);
        
        // Revertir estados a error
        Object.keys(cards).forEach(source => {
            updateCardStatus(source, 'Error', 0, 'Fallo');
        });
    } finally {
        // Desbloquear controles
        btnStart.disabled = false;
        queryInput.disabled = false;
        limitSelect.disabled = false;
    }
}

// Actualizar visualmente la tarjeta de una red social
function updateCardStatus(source, status, count, type) {
    const card = cards[source];
    if (!card) return;

    const indicator = card.querySelector('.status-indicator');
    const dot = card.querySelector('.indicator-dot');
    const statusText = card.querySelector('.status-text');
    const countDisplay = card.querySelector('.extracted-count');
    const badge = card.querySelector('.type-badge');

    // Clases de la bolita de estado
    dot.className = 'indicator-dot';
    if (status === 'Pendiente') {
        dot.classList.add('dot-pending');
        statusText.style.color = 'var(--color-pending)';
    } else if (status === 'Extrayendo...') {
        dot.classList.add('dot-loading');
        statusText.style.color = 'var(--color-warning)';
    } else if (status === 'Completado') {
        dot.classList.add('dot-success');
        statusText.style.color = 'var(--color-success)';
    } else {
        dot.classList.add('dot-pending');
        statusText.style.color = '#ef4444'; // Rojo para error
    }

    statusText.innerText = status;
    countDisplay.innerHTML = `${count} <span class="count-unit">registros</span>`;

    // Etiqueta de tipo de extracción
    badge.innerText = type;
    badge.className = 'badge type-badge';
    if (type.includes('Real')) {
        badge.classList.add('api');
    } else if (type.includes('Simulación')) {
        badge.classList.add('sim');
    }
}

// Actualizar métricas generales de la barra resumen
function updateMetrics(total, duration) {
    document.getElementById('metricTotal').innerText = total;
    
    const speed = duration > 0 ? (total / duration).toFixed(1) : 0;
    document.getElementById('metricSpeed').innerText = `${speed} /s`;
}

// Renderizar la tabla de registros aplicando filtros y búsquedas locales
function renderTable() {
    // Filtrar dataset local
    const filteredData = localDataset.filter(item => {
        // Filtro de pestaña lateral
        const matchesFilter = (activeFilter === 'all' || item.source === activeFilter);
        
        // Filtro de barra de búsqueda rápida
        const matchesSearch = !activeSearchQuery || 
            item.title.toLowerCase().includes(activeSearchQuery) ||
            item.text.toLowerCase().includes(activeSearchQuery) ||
            item.author.toLowerCase().includes(activeSearchQuery);
            
        return matchesFilter && matchesSearch;
    });

    // Limpiar tabla
    tableBody.innerHTML = '';

    if (filteredData.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="no-data">No se encontraron registros que coincidan con los filtros aplicados.</td>
            </tr>
        `;
        return;
    }

    // Insertar registros
    filteredData.forEach(item => {
        const tr = document.createElement('tr');
        
        // Parsear métricas de interacción
        let metricsHtml = '';
        try {
            const metricsObj = JSON.parse(item.metrics);
            Object.entries(metricsObj).forEach(([key, val]) => {
                let label = key;
                if (key === 'upvotes') label = 'Votos';
                else if (key === 'points') label = 'Puntos';
                else if (key === 'comments') label = 'Comentarios';
                else if (key === 'likes') label = 'Likes';
                else if (key === 'replies') label = 'Respuestas';
                else if (key === 'views') label = 'Vistas';
                
                metricsHtml += `<span><strong>${label}:</strong> ${val.toLocaleString()}</span>`;
            });
        } catch (e) {
            metricsHtml = '<span>Sin métricas</span>';
        }

        // Determinar clase CSS y archivo de imagen para el badge de la fuente
        let sourceClass = item.source.toLowerCase();
        let imgName = sourceClass;
        if (sourceClass === 'hacker news') {
            sourceClass = 'hackernews';
            imgName = 'hackernews';
        }

        tr.innerHTML = `
            <td>
                <span class="row-source ${sourceClass}">
                    <img src="${imgName}.png" class="table-icon" alt="${item.source}">
                    ${item.source}
                </span>
            </td>
            <td class="author-cell">${item.author}</td>
            <td class="text-cell">
                <h4>${escapeHtml(item.title)}</h4>
                <p>${escapeHtml(item.text)}</p>
            </td>
            <td class="date-cell">${item.date}</td>
            <td class="metrics-cell">${metricsHtml}</td>
            <td class="link-cell">
                <a href="${item.url}" target="_blank">
                    Ver origen
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                </a>
            </td>
        `;
        
        tableBody.appendChild(tr);
    });
}

// Utilidad para evitar XSS
function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

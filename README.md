# FAQ Bot API - Sistema de Preguntas y Respuestas con IA

Un chatbot inteligente que responde preguntas frecuentes (FAQs) usando **búsqueda semántica** y **generación con IA** (Google Gemini). 

## 🎯 ¿Qué hace?

El bot busca las respuestas más relevantes en tu base de datos PostgreSQL, las ordena por similitud semántica usando **vectores**, y luego las reescribe de forma natural con **Gemini** para una mejor experiencia del usuario.

---

## 📋 Requisitos Previos

- **Docker y Docker Compose** instalados
- **Archivo `.env`** con las credenciales (ver [Configuración](#-configuración))
- *(Opcional)* curl o Postman para probar

---

## 🚀 Inicio Rápido

### 1. Preparar el archivo `.env`

Crea un archivo `.env` en la raíz del proyecto:

```bash
# Base de datos PostgreSQL (RDS)
DATABASE_URL=postgresql://user:password@host:5432/dbname?sslmode=require

# O bien, variables individuales:
DB_HOST=tu-rds.amazonaws.com
DB_PORT=5432
DB_NAME=tu_base_datos
DB_USERNAME=admin
DB_PASSWORD=tu_contraseña
DB_SSLMODE=require

# Tabla y columnas personalizables
DB_TABLE=public.helper_questions
DB_COL_ID=id
DB_COL_SEGMENT_ID=segment_id
DB_COL_QUESTION=question
DB_COL_RESPONSE=response
DB_COL_LINK=link
DB_COL_CREATED_AT=created_at

# Google Gemini (para embeddings y generación)
GEMINI_API_KEY=tu_clave_gemini_aqui

# Qdrant (vector database)
QDRANT_URL=http://localhost:6333

# Configuración RAG
RAG_TOP_K=5
RAG_HIGH_THRESHOLD=0.75
ALWAYS_RAG=true
```

### 2. Levantar los contenedores

**Terminal 1:** Inicia Docker Compose

```bash
docker compose up --build
```

Espera a que veas algo como:
```
api-1     | INFO:     Uvicorn running on http://0.0.0.0:8080
qdrant-1  | [2024-11-11 10:30:15] ... Server started
```

### 3. Indexar las FAQs en Qdrant (Primera vez - IMPORTANTE)

**Terminal 2:** Sin datos indexados, las búsquedas no funcionan. Hay dos opciones:

#### Opción A: Indexar desde el archivo seed (recomendado para desarrollo)
```bash
curl -s -X POST http://localhost:8080/reindex \
  -H 'Content-Type: application/json' \
  -d '{"source": "seed"}' | jq
```

Respuesta esperada:
```json
{
  "upserts": 3,
  "skipped": 0,
  "duration_ms": 1245
}
```

Esto carga 3 FAQs de ejemplo desde `packages/config/seed_faqs.json`.

#### Opción B: Indexar desde PostgreSQL (si ya hay FAQs en la BD)
```bash
curl -s -X POST http://localhost:8080/reindex \
  -H 'Content-Type: application/json' \
  -d '{"source": "db", "full": true}' | jq
```

Esto lee todas las FAQs de la tabla PostgreSQL, las convierte a vectores y las guarda en Qdrant.

### 4. Probar el API

**Terminal 2 (después de indexar):** Haz los primeros curls

#### a) Salud del servicio
```bash
curl -s http://localhost:8080/health | jq
```

Respuesta esperada:
```json
{
  "status": "ok"
}
```

#### b) Hacer una pregunta
```bash
curl -s -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "¿Cuál es el horario de atención?",
    "role": "Secretaria",
    "lang": "es"
  }' | jq
```

Respuesta esperada:
```json
{
  "mode": "RAG",
  "answer": "Nuestro horario es de lunes a viernes de 9:00 a 17:00 horas.",
  "sources": [
    {
      "faq_id": 1,
      "segment_id": 11,
      "score": 0.85,
      "link": "https://ejemplo.com/horarios"
    }
  ],
  "meta": {
    "top_k": 5,
    "latency_ms": 234,
    "trace_id": null
  }
}
```

#### c) Probar con diferentes roles
```bash
# Rol "Gerencia" (solo ve FAQs del segmento 15, 16, 17)
curl -s -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "¿Cuál es el presupuesto?",
    "role": "Gerencia"
  }' | jq

# Rol "public" (ve todo)
curl -s -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "¿Quiénes somos?",
    "role": "public"
  }' | jq
```

---

## ⏱️ Primeros 5 Minutos (Checklist)

Para levantar el proyecto por primera vez:

```bash
# 1️⃣ Terminal 1: Levantar Docker
docker compose up --build

# (esperar a que veas "INFO: Uvicorn running on http://0.0.0.0:8080")

# 2️⃣ Terminal 2: Indexar FAQs en Qdrant (CRUCIAL)
curl -s -X POST http://localhost:8080/reindex \
  -H 'Content-Type: application/json' \
  -d '{"source": "seed"}' | jq

# (esperar respuesta con "upserts": 3)

# 3️⃣ Terminal 2: Verificar que funciona
curl -s http://localhost:8080/health | jq

# 4️⃣ Terminal 2: Hacer una pregunta
curl -s -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "¿Cuál es el horario?", "role": "public"}' | jq
```

Si ves respuesta en el último paso ✅ ¡Listo!

Si no hay respuesta o error "NO_RESULTS_FOR_ROLE", revisa:
1. ¿Se ejecutó el `/reindex`? (debe devolver `upserts > 0`)
2. ¿Los roles están en `packages/config/roles.json`?
3. ¿Los `segment_id` de las FAQs coinciden con los roles?

---

```
faqbot/
├── apps/
│   └── api/                  # FastAPI + endpoints REST
│       ├── main.py           # Configuración de la app
│       ├── routers/
│       │   ├── chat.py       # Endpoint POST /chat
│       │   ├── health.py     # Endpoint GET /health
│       │   └── reindex.py    # Admin: reindexar FAQs
│       └── schemas/          # Validación de requests/responses
│
├── packages/
│   ├── adapters/             # Integraciones externas
│   │   ├── db/sql.py         # Lectura desde PostgreSQL
│   │   ├── llm/gemini.py     # Embeddings + generación con Google
│   │   ├── vector/qdrant_store.py  # Base de datos vectorial
│   │   └── telemetry/        # Logging
│   │
│   ├── core/                 # Lógica de negocio
│   │   ├── retrieval.py      # Búsqueda semántica
│   │   ├── roles.py          # Control de acceso por rol
│   │   └── types.py          # Tipos comunes
│   │
│   └── config/               # Configuración
│       ├── settings.py       # Variables de entorno (.env)
│       ├── roles.json        # Mapeo de roles → segmentos
│       └── seed_faqs.json    # FAQs de ejemplo
│
├── services/
│   └── indexer/run.py        # Script para indexar FAQs en Qdrant
│
├── docker-compose.yml        # Orquestación de servicios
├── Dockerfile                # Imagen del API
└── requirements.txt          # Dependencias Python
```

---

## 🧠 Cómo Funciona

### 1. **Flujo de una pregunta**

```
Usuario pregunta: "¿Horarios?"
        ↓
   [1] Obtener rol → validar acceso
        ↓
   [2] Convertir pregunta a vector (Google Gemini embedding)
        ↓
   [3] Buscar en Qdrant (similaridad coseno) top-5 FAQs permitidas
        ↓
   [4] Decidir: ¿respuesta exacta o regenerar con IA?
        ↓
   [5] Si exacta: devolver respuesta de FAQ directamente
        Si RAG: reescribir con contexto usando Gemini
        ↓
   Devolver respuesta + fuentes + metadata
```

### 2. **Retrieval (búsqueda semántica)**

Archivo: `packages/core/retrieval.py`

```python
def retrieve(query: str, allowed_segments: List[int], top_k: int = 5):
    # 1. Convertir pregunta a vector
    vec = embed_queries([query])[0]  # Lista [0.1, 0.2, ..., 0.8]
    
    # 2. Buscar en Qdrant
    store = QdrantStore()
    res = store.search(vec, allowed_segments, top_k)
    
    # 3. Devolver resultados ordenados
    return [(faq_id, segment_id, score, link, answer, question), ...]
```

**Puntuación:** similaridad coseno entre 0 (diferente) y 1 (idéntico)

### 3. **Decisión: Exacto vs RAG**

Archivo: `apps/api/routers/chat.py`

```python
best_score = results_sorted[0][2]

# Si score alto (>0.75) y no hay "ALWAYS_RAG":
if best_score >= RAG_HIGH_THRESHOLD and not ALWAYS_RAG:
    answer = best[4]  # Respuesta exacta de la FAQ
    mode = "EXACT"
else:
    # Usar contexto para generar respuesta mejorada
    answer = generate_answer(question, context_docs)
    mode = "RAG"
```

### 4. **Generación RAG (Retrieval Augmented Generation)**

Archivo: `packages/adapters/llm/gemini.py`

```python
def generate_answer(question: str, context_docs: List[Dict]) -> str:
    context_block = "\n---\n".join([
        f"Q: {d['question']}\nA: {d['answer']}"
        for d in context_docs
    ])
    
    # Prompt con instrucciones
    prompt = f"""
    Usuario: {question}
    
    CONTEXTO (solo responder con esto):
    {context_block}
    
    Instrucciones: Responde SOLO basándote en el contexto, de forma concisa.
    """
    
    # Gemini genera la respuesta
    res = model.generate_content(prompt)
    return res.text
```

### 5. **Control de Acceso por Rol**

Archivo: `packages/config/roles.json`

```json
{
  "Secretaria": [11, 12, 13],           # Solo ve FAQs de estos segmentos
  "Gerencia": [15, 16, 17],
  "public": [11, 12, 13, 15, 16, 17]    # Ve todo
}
```

Cuando alguien pregunta con rol "Secretaria", solo busca en los segmentos 11, 12, 13.

---

## 🔧 Configuración (`.env`)

| Variable | Descripción | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Conexión Postgres (o usar DB_HOST, DB_PORT, etc.) | - |
| `GEMINI_API_KEY` | Clave de Google Gemini | - |
| `QDRANT_URL` | URL de Qdrant | `http://localhost:6333` |
| `COLLECTION_NAME` | Nombre de colección en Qdrant | `faq_es_v1` |
| `RAG_TOP_K` | Cuántas FAQs traer (top-k) | `5` |
| `RAG_HIGH_THRESHOLD` | Score mínimo para respuesta exacta | `0.75` |
| `ALWAYS_RAG` | Siempre regenerar con IA (no usar exactas) | `true` |
| `ROLES_CONFIG_PATH` | Ruta a roles.json | `packages/config/roles.json` |
| `LANG_DEFAULT` | Idioma por defecto | `es` |

---

## 📊 Herramientas Útiles

### Ver datos en la base de datos

Ejecuta dentro del contenedor:

```bash
# Últimas 10 FAQs indexadas
docker exec -i faqbot-api-1 python - <<'PY'
import psycopg
from psycopg import sql
from packages.config.settings import settings

dsn = settings.pg_dsn()
schema, table = ("public", settings.DB_TABLE)
if "." in settings.DB_TABLE:
    schema, table = settings.DB_TABLE.split(".", 1)

c_id  = settings.DB_COL_ID
c_seg = settings.DB_COL_SEGMENT_ID
c_q   = settings.DB_COL_QUESTION
c_r   = settings.DB_COL_RESPONSE
c_lnk = settings.DB_COL_LINK
c_crt = settings.DB_COL_CREATED_AT

link_expr = sql.Identifier(c_lnk) if c_lnk else sql.SQL("NULL")
created_expr = sql.Identifier(c_crt) if c_crt else sql.SQL("NULL")

q = sql.SQL("""
SELECT
  {id}   AS id,
  {seg}  AS segment_id,
  {qcol} AS question,
  {rcol} AS response
FROM {schema}.{table}
ORDER BY {id} DESC
LIMIT 10
""").format(
    id=sql.Identifier(c_id),
    seg=sql.Identifier(c_seg),
    qcol=sql.Identifier(c_q),
    rcol=sql.Identifier(c_r),
    lnk=link_expr,
    crt=created_expr,
    schema=sql.Identifier(schema),
    table=sql.Identifier(table),
)

with psycopg.connect(dsn) as conn, conn.cursor() as cur:
    cur.execute(q)
    for id_, seg, ques, resp in cur.fetchall():
        print(f"[{id_}] seg={seg}  Q: {ques[:60]}...")
PY
```

### Acceder a la consola de Qdrant

```
http://localhost:6335
```

Ves las colecciones de vectores, búsquedas, etc.

---

## 🧪 Tests

Ejecuta los tests unitarios:

```bash
python -m pytest tests/ -v
```

---

## 📚 Módulos Principales

### `packages/adapters/llm/gemini.py`
- **`embed_documents(texts)`** → Convertir FAQs a vectores (Google Embedding)
- **`embed_queries(texts)`** → Convertir preguntas a vectores
- **`generate_answer(question, context_docs)`** → Generar respuesta con Gemini

### `packages/adapters/vector/qdrant_store.py`
- **`ensure_collection()`** → Crear colección si no existe
- **`upsert(items, vectors)`** → Guardar FAQs + vectores
- **`search(query_vector, allowed_segments, top_k)`** → Buscar por similitud

### `packages/core/retrieval.py`
- **`retrieve(query, allowed_segments, top_k)`** → Orquesta embeddings + búsqueda

### `packages/config/settings.py`
- **`load_roles()`** → Cargar mapeo de roles desde roles.json
- **`pg_dsn()`** → Construir string de conexión PostgreSQL

---

## 🐛 Troubleshooting

### "Olvidé hacer el reindex al inicio"
No hay problema, ejecuta:
```bash
curl -s -X POST http://localhost:8080/reindex \
  -H 'Content-Type: application/json' \
  -d '{"source": "seed"}' | jq
```

Si tienes datos en PostgreSQL y quieres indexar desde ahí:
```bash
curl -s -X POST http://localhost:8080/reindex \
  -H 'Content-Type: application/json' \
  -d '{"source": "db", "full": true}' | jq
```

### "No hay conexión a Qdrant"
```bash
# Verifica que el contenedor está corriendo
docker ps | grep qdrant

# Intenta conectar
curl http://localhost:6335/health
```

### "ROLE_NOT_MAPPED"
Verifica que el rol esté en `packages/config/roles.json` y usa el nombre exacto:
```bash
curl -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "Hola", "role": "Secretaria"}'  # Exacto como en JSON
```

### "NO_RESULTS_FOR_ROLE"
No hay FAQs en los segmentos permitidos para ese rol. Verifica:
1. Que existan FAQs en esa BD
2. Que los segment_id coincidan con los de roles.json
3. Que hayan sido indexadas (ejecuta `/reindex` endpoint)

---

## 🚀 Próximas Mejoras

- [ ] Caché Redis para respuestas recurrentes
- [ ] Análisis de feedback (mejora iterativa)
- [ ] Soporte para múltiples idiomas automático
- [ ] Dashboard de admin para editar FAQs

---

## 📄 Licencia

MIT



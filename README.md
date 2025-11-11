* Como probar el chat

```
curl -s -X POST http://localhost:8080/chat \
  -H 'content-type: application/json' \
  -d '{"message":"¿horarios de atención?","role":"Secretaria"}' | jq
```


* Comandos listos para ver muestras reales de la tabla desde dentro del contenedor (usando el mismo DSN que usa tu app). Así podés ver qué preguntar y validar que el bot responde bien. Usar en la consola

* A) 10 filas recientes (preview de respuesta)
```
docker exec -i faqbot-api-1 python - <<'PY'
import psycopg, textwrap
from psycopg import sql
from packages.config.settings import settings

dsn = settings.pg_dsn()
schema, table = ("public", settings.DB_TABLE)
if "." in settings.DB_TABLE:
    schema, table = settings.DB_TABLE.split(".", 1)

# Column mapping (desde settings)
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
  {seg}  AS "segmentId",
  {qcol} AS question,
  {rcol} AS response,
  {lnk}  AS link,
  {crt}  AS "createdAt"
FROM {schema}.{table}
ORDER BY {crt} DESC NULLS LAST, {id} DESC
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

def trunc(s, n=110):
    s = "" if s is None else str(s)
    return (s[:n] + "…") if len(s) > n else s

with psycopg.connect(dsn) as conn, conn.cursor() as cur:
    cur.execute(q)
    rows = cur.fetchall()
    for i, (id_, seg, ques, resp, link, crt) in enumerate(rows, 1):
        print(f"[{i}] id={id_}  segmentId={seg}  createdAt={crt}")
        print(" Q:", trunc(ques))
        print(" A:", trunc(resp))
        if link: print(" L:", trunc(link, 120))
        print("-"*80)
PY
```

B) 3 filas por cada segmentId (muestra balanceada)
```
docker exec -i faqbot-api-1 python - <<'PY'
import psycopg
from psycopg import sql
from packages.config.settings import settings

dsn = settings.pg_dsn()
schema, table = ("public", settings.DB_TABLE)
if "." in settings.DB_TABLE:
    schema, table = settings.DB_TABLE.split(".", 1)

c_id, c_seg, c_q, c_r, c_lnk, c_crt = (
    settings.DB_COL_ID, settings.DB_COL_SEGMENT_ID, settings.DB_COL_QUESTION,
    settings.DB_COL_RESPONSE, settings.DB_COL_LINK, settings.DB_COL_CREATED_AT
)

link_expr = sql.Identifier(c_lnk) if c_lnk else sql.SQL("NULL")
created_expr = sql.Identifier(c_crt) if c_crt else sql.SQL("NULL")

q = sql.SQL("""
WITH ranked AS (
  SELECT
    {id}   AS id,
    {seg}  AS "segmentId",
    {qcol} AS question,
    {rcol} AS response,
    {lnk}  AS link,
    {crt}  AS "createdAt",
    ROW_NUMBER() OVER (
      PARTITION BY {seg}
      ORDER BY {crt} DESC NULLS LAST, {id} DESC
    ) AS rn
  FROM {schema}.{table}
)
SELECT * FROM ranked WHERE rn <= 3 ORDER BY "segmentId", rn;
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
    for row in cur.fetchall():
        print(f"seg={row[1]}  id={row[0]}  rn={row[6]}  Q={row[2][:80]}  A={row[3][:80]}")
PY
```



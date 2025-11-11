# packages/adapters/db/sql.py
from __future__ import annotations
from typing import Iterator, Dict, Any, List, Optional, Any as AnyT
from datetime import datetime
import psycopg
from psycopg.rows import dict_row
from psycopg import sql
from packages.config.settings import settings

class DbFaqReader:
    """
    Lee FAQs desde Postgres y devuelve batches con el shape:
      { faq_id, segment_id, question, response, link, created_at }
    Usa nombres de columna desde settings.DB_COL_*.
    """

    def __init__(self):
        dsn = settings.pg_dsn()
        if not dsn:
            raise RuntimeError("DATABASE_URL o DB_* no configurados")
        self.dsn = dsn

        self.schema, self.table = ("public", settings.DB_TABLE)
        if "." in settings.DB_TABLE:
            self.schema, self.table = settings.DB_TABLE.split(".", 1)

        # Column mapping desde settings
        self.col_id = settings.DB_COL_ID
        self.col_seg = settings.DB_COL_SEGMENT_ID
        self.col_q = settings.DB_COL_QUESTION
        self.col_r = settings.DB_COL_RESPONSE
        self.col_link = settings.DB_COL_LINK
        self.col_created = settings.DB_COL_CREATED_AT
        self.col_updated = settings.DB_COL_UPDATED_AT
        self.col_active = settings.DB_COL_IS_ACTIVE
        self.active_true = settings.DB_ACTIVE_TRUE

    def iter_faqs(self, since_iso: Optional[str] = None, batch_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
        where_parts: List[sql.SQL] = []

        if self.col_active:
            # e.g. is_active = TRUE
            where_parts.append(
                sql.SQL("{} = " + self.active_true).format(sql.Identifier(self.col_active))
            )

        params: List[AnyT] = []
        if since_iso and self.col_updated:
            where_parts.append(sql.SQL("{} >= %s").format(sql.Identifier(self.col_updated)))
            params.append(since_iso)

        where_sql = sql.SQL("")
        if where_parts:
            where_sql = sql.SQL(" WHERE ") + sql.SQL(" AND ").join(where_parts)

        link_expr = sql.Identifier(self.col_link) if self.col_link else sql.SQL("NULL")
        created_expr = sql.Identifier(self.col_created) if self.col_created else sql.SQL("NULL")

        query = sql.SQL("""
            SELECT
                {id}   AS faq_id,
                {seg}  AS segment_id,
                {q}    AS question,
                {r}    AS response,
                {lnk}  AS link,
                {crt}  AS created_at
            FROM {schema}.{table}
            {where}
            ORDER BY {id} ASC
        """).format(
            id=sql.Identifier(self.col_id),
            seg=sql.Identifier(self.col_seg),
            q=sql.Identifier(self.col_q),
            r=sql.Identifier(self.col_r),
            lnk=link_expr,
            crt=created_expr,
            schema=sql.Identifier(self.schema),
            table=sql.Identifier(self.table),
            where=where_sql,
        )

        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            with conn.cursor(name="faqbot_stream") as cur:
                cur.itersize = batch_size
                cur.execute(query, params)
                batch: List[Dict[str, Any]] = []
                for row in cur:
                    item = {
                        "faq_id": int(row["faq_id"]),
                        "segment_id": int(row["segment_id"]),
                        "question": (row["question"] or "").strip(),
                        "response": (row["response"] or "").strip(),
                        "link": row.get("link"),
                        "created_at": (
                            row.get("created_at").isoformat()
                            if isinstance(row.get("created_at"), datetime)
                            else row.get("created_at")
                        ),
                    }
                    batch.append(item)
                    if len(batch) >= batch_size:
                        yield batch
                        batch = []
                if batch:
                    yield batch

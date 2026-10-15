"""CKAN DataStore tools: tabular query and SQL."""

from __future__ import annotations

import json
import re

import sqlparse
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field
from sqlparse import sql as sqltree
from sqlparse import tokens as T

from ..app import mcp
from ..formatters import handle_api_error
from ..http_client import ckan_request

# Every DataStore table is named after its CKAN resource id.
_RESOURCE_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)
# Keywords that end a FROM clause: after them a comma separates columns or
# rows, not relations.
_CLAUSE_END = ("GROUP BY", "ORDER BY", "HAVING", "LIMIT", "OFFSET", "WINDOW", "FETCH", "FOR")
_SET_OPS = ("UNION", "INTERSECT", "EXCEPT")


def _meaningful(group: sqltree.TokenList) -> list[sqltree.Token]:
    return [t for t in group.tokens if not t.is_whitespace and t.ttype not in T.Comment]


def _starts_query(paren: sqltree.Parenthesis) -> bool:
    inner = _meaningful(paren)[1:]
    return bool(inner) and inner[0].ttype in (T.DML, T.CTE)


def _defined_ctes(group: sqltree.TokenList) -> set[str]:
    """CTE names a WITH at THIS level defines. They are visible here and below,
    never beside: `(WITH users AS (…) …) s, users` still reads the real table."""
    tokens = _meaningful(group)
    names: set[str] = set()
    for i, tok in enumerate(tokens):
        if tok.ttype is not T.CTE:
            continue
        rest = [t for t in tokens[i + 1 :] if t.normalized != "RECURSIVE"]
        if rest and isinstance(rest[0], sqltree.IdentifierList):
            defined = list(rest[0].get_identifiers())
        else:
            defined = rest[:1]
        for d in defined:
            if isinstance(d, sqltree.Identifier) and d.get_real_name():
                names.add(str(d.get_real_name()).lower())
    return names


def _check_relation(ref: sqltree.Token, ctes: set[str], foreign: list[str]) -> None:
    """The token where a FROM list names a relation: a resource table, a CTE,
    or a subquery. Anything else is refused."""
    if isinstance(ref, sqltree.Parenthesis) and _starts_query(ref):
        _walk(ref, ctes, foreign, in_function=False)
        return
    name: str | None = None
    if isinstance(ref, sqltree.Identifier):
        subquery = next((t for t in ref.tokens if isinstance(t, sqltree.Parenthesis)), None)
        if subquery is not None and _starts_query(subquery):
            _walk(subquery, ctes, foreign, in_function=False)
            return
        plain = subquery is None and not any(isinstance(t, sqltree.Function) for t in ref.tokens)
        if plain and ref.get_parent_name() is None:
            name = ref.get_real_name()
    if name and (name.lower() in ctes or _RESOURCE_ID.fullmatch(name)):
        return
    # A schema-qualified name, a table function, a keyword sqlparse did not
    # group (`user`, `role`, `session` are relation names to PostgreSQL), a
    # parenthesised join: none of them is a resource table. Failing closed is
    # the point of the gate. Only the first word is reported, so a quoted name
    # cannot carry a sentence into the reply.
    foreign.append(str(ref).split()[0][:40])


def _walk(
    group: sqltree.TokenList, inherited: set[str], foreign: list[str], in_function: bool
) -> None:
    """Find every relation `group` reads.

    The position decides, not the token type: a relation is whatever stands
    right after FROM, JOIN, TABLE or a comma in a FROM list (LATERAL and ONLY
    only qualify it). What follows it, an alias or an ON / USING condition, is
    not one. sqlparse groups `ON a.x = b.x, users c` into ONE IdentifierList, so
    a list inside a FROM clause is read token by token in this same state,
    never as a unit.
    """
    ctes = inherited | _defined_ctes(group)
    in_from = expect = False
    prev: sqltree.Token | None = None

    def visit(tok: sqltree.Token) -> None:
        nonlocal in_from, expect, prev
        word = tok.normalized if tok.ttype in T.Keyword else ""
        if word.startswith(_SET_OPS) or word in _CLAUSE_END:
            in_from = expect = False
        elif word in ("FROM", "TABLE") or word.endswith("JOIN"):
            # `EXTRACT(YEAR FROM …)`, `SUBSTRING(… FROM 1)` and
            # `IS DISTINCT FROM` use FROM without naming a table.
            distinct = prev is not None and prev.normalized == "DISTINCT"
            in_from = expect = not in_function and not distinct
        elif in_from and isinstance(tok, sqltree.IdentifierList):
            for item in _meaningful(tok):
                visit(item)
            return
        elif in_from and tok.match(T.Punctuation, ","):
            expect = True
        elif expect and word in ("LATERAL", "ONLY"):
            pass
        elif expect:
            _check_relation(tok, ctes, foreign)
            expect = False
        elif isinstance(tok, sqltree.Function):
            _walk(tok, ctes, foreign, in_function=True)
        elif isinstance(tok, sqltree.Parenthesis):
            _walk(tok, ctes, foreign, in_function and not _starts_query(tok))
        elif isinstance(tok, sqltree.TokenList):
            _walk(tok, ctes, foreign, in_function)
        prev = tok

    for tok in _meaningful(group):
        visit(tok)


def _foreign_tables(statement: sqltree.Statement) -> list[str]:
    """Every relation the statement reads that is neither a DataStore resource
    nor a CTE it defines itself."""
    foreign: list[str] = []
    _walk(statement, set(), foreign, in_function=False)
    return foreign


def _validate_select_only(sql: str) -> str | None:
    # Defense-in-depth gate: CKAN's datastore_search_sql role is read-only,
    # but we still want a friendly client-side error and to refuse stacked
    # statements (`SELECT 1; DROP TABLE foo`) and non-read DDL/DML up front.
    # sqlparse handles quoted strings, comments, and CTEs (`WITH … SELECT`
    # is reported as type "SELECT").
    statements = [s for s in sqlparse.parse(sql) if str(s).strip()]
    if not statements:
        return "Fehler: SQL-Abfrage ist leer."
    if len(statements) > 1:
        return (
            "Fehler: Nur einzelne Statements sind erlaubt. "
            "Mehrere durch ';' getrennte Anweisungen werden nicht akzeptiert."
        )
    if statements[0].get_type() != "SELECT":
        return (
            "Fehler: Nur SELECT-Abfragen sind erlaubt (CTEs mit WITH … SELECT "
            "ebenfalls). DROP, INSERT, UPDATE, DELETE und andere Statements "
            "sind nicht gestattet."
        )
    # A single SELECT can still read any relation the database role sees —
    # `… UNION SELECT … FROM pg_user`. CKAN checks table permissions itself;
    # this keeps the tool to what it is for, and says so before any request.
    foreign = _foreign_tables(statements[0])
    if foreign:
        return (
            "Fehler: Abfragen dürfen nur DataStore-Ressourcen lesen. Tabellen "
            'werden als Ressourcen-ID in Anführungszeichen angegeben, z. B. FROM "<uuid>"; '
            "die IDs liefert zurich_get_dataset. Nicht erlaubt: "
            + ", ".join(list(dict.fromkeys(foreign))[:3])
        )
    return None


class DatastoreQueryInput(BaseModel):
    """Input für Datastore-Abfragen."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    resource_id: str = Field(
        ...,
        description="Resource-ID aus dem Datensatz (UUID-Format)",
        min_length=1,
    )
    filters: str | None = Field(
        default=None,
        description='JSON-Filter, z.B. {"Quartier": "Wiedikon"} oder {"Jahr": 2024}',
    )
    query: str | None = Field(
        default=None,
        description="Volltextsuche innerhalb der Ressource",
    )
    sort: str | None = Field(
        default=None,
        description="Sortierung, z.B. 'Jahr desc'",
    )
    limit: int = Field(default=20, description="Anzahl Datensätze (max. 100)", ge=1, le=100)
    offset: int = Field(default=0, description="Offset für Paginierung", ge=0)


@mcp.tool(
    name="zurich_datastore_query",
    annotations=ToolAnnotations(
        title="Tabellarische Daten abfragen",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def zurich_datastore_query(params: DatastoreQueryInput) -> str:
    """Fragt tabellarische Daten direkt aus dem CKAN DataStore ab.

    Ermöglicht gefilterte Abfragen auf Ressourcen, die im DataStore
    gespeichert sind (CSV-Daten werden automatisch indexiert).

    Returns:
        Markdown-Tabelle mit Daten und Feld-Informationen
    """
    try:
        api_params: dict = {
            "resource_id": params.resource_id,
            "limit": params.limit,
            "offset": params.offset,
        }
        if params.filters:
            try:
                json.loads(params.filters)
            except (json.JSONDecodeError, TypeError):
                return (
                    "Fehler: `filters` muss gültiges JSON sein, "
                    'z.B. `{"Quartier": "Wiedikon"}`. '
                    f"Erhalten: `{params.filters[:100]}`"
                )
            api_params["filters"] = params.filters
        if params.query:
            api_params["q"] = params.query
        if params.sort:
            api_params["sort"] = params.sort

        result = await ckan_request("datastore_search", api_params)
        total = result.get("total", 0)
        records = result.get("records", [])
        fields = result.get("fields", [])

        if not records:
            return "Keine Daten gefunden."

        # Field info
        field_info = [f"- `{f['id']}` ({f.get('type', '?')})" for f in fields if f["id"] != "_id"]

        lines = [
            f"## DataStore-Abfrage: {total} Einträge",
            f"Zeige {len(records)} (Offset: {params.offset})\n",
            "### Felder",
            "\n".join(field_info),
            "\n### Daten\n",
            "```json",
            json.dumps(records[: params.limit], indent=2, ensure_ascii=False, default=str),
            "```",
        ]

        if total > params.offset + len(records):
            lines.append(f"\n*→ Weitere mit offset={params.offset + len(records)}*")

        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "DataStore-Abfrage")


class DatastoreSqlInput(BaseModel):
    """Input für SQL-Abfragen auf dem DataStore."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    sql: str = Field(
        ...,
        description=(
            "SQL-Abfrage auf den DataStore. Tabellen sind Ressourcen-IDs in "
            "Anführungszeichen (andere Tabellen werden abgelehnt). "
            'Beispiel: SELECT * FROM "resource-uuid" WHERE "Jahr" = 2024 LIMIT 10'
        ),
        min_length=5,
    )


@mcp.tool(
    name="zurich_datastore_sql",
    annotations=ToolAnnotations(
        title="SQL-Abfrage auf DataStore",
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    ),
)
async def zurich_datastore_sql(params: DatastoreSqlInput) -> str:
    """Führt eine SQL-Abfrage auf dem CKAN DataStore aus.

    Ermöglicht komplexe Abfragen mit JOINs, UNION, GROUP BY, Aggregationen etc.
    Nur SELECT-Abfragen sind erlaubt, und nur auf DataStore-Ressourcen: Jede
    Tabelle ist eine Ressourcen-ID in Anführungszeichen (aus zurich_get_dataset).

    Returns:
        JSON-Ergebnisse der SQL-Abfrage
    """
    try:
        validation_error = _validate_select_only(params.sql)
        if validation_error:
            return validation_error

        result = await ckan_request("datastore_search_sql", {"sql": params.sql})
        records = result.get("records", [])
        fields = result.get("fields", [])

        if not records:
            return "SQL-Abfrage lieferte keine Ergebnisse."

        # `_full_text` is CKAN's tsvector search index, which `SELECT *` hands
        # back with every row (`'+0100':6 '-01':2,3 '/m3':12 …`). It costs
        # tokens and means nothing to a reader, so it leaves the column list
        # AND the records; `_id` only the column list, as before. Told apart
        # by its type, not its name alone: `COUNT(*) AS "_full_text"` is a
        # column the caller asked for (int8) and stays.
        index = {f["id"] for f in fields if f["id"] == "_full_text" and f.get("type") == "tsvector"}
        field_names = [f["id"] for f in fields if f["id"] != "_id" and f["id"] not in index]
        records = [{k: v for k, v in r.items() if k not in index} for r in records]

        lines = [
            f"## SQL-Ergebnis: {len(records)} Zeilen",
            f"**Spalten**: {', '.join(field_names)}\n",
            "```json",
            json.dumps(records, indent=2, ensure_ascii=False, default=str),
            "```",
        ]
        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "SQL-Abfrage")

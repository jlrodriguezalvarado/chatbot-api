# app/aplication/vector_store.py
import io
import re
from typing import Optional, List

from openai import OpenAI
from sqlalchemy import text
from flask import current_app

def _slug(s: str, maxlen: int = 60) -> str:
    import re as _re
    s = _re.sub(r"\s+", "-", (s or "").strip().lower())
    s = _re.sub(r"[^a-z0-9\-]+", "", s)
    return s[:maxlen] or "post"

def _read_vector_store_id(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip() or None
    except FileNotFoundError:
        return None

def _write_vector_store_id(path: str, vs_id: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(vs_id.strip())

def build_vector_store_from_posts(db_engine, *, table: str = "post", limit: Optional[int] = None) -> str:
    """
    Lee (id,title,content) desde PostgreSQL y hace upsert en un Vector Store gestionado por OpenAI.
    Guarda el id en current_app.config['VECTOR_STORE_ID_FILE'] y lo retorna.
    """
    cfg = current_app.config
    if not cfg.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY no configurada")

    client = OpenAI()

    q = f"SELECT id, title, content FROM {table}"
    if limit:
        q += f" LIMIT {int(limit)}"

    with db_engine.connect() as conn:
        rows = conn.execute(text(q)).mappings().all()

    if not rows:
        raise RuntimeError("No se encontraron posts en la tabla.")

    vs_id_file = cfg["VECTOR_STORE_ID_FILE"]
    vs_id = _read_vector_store_id(vs_id_file)

    if vs_id:
        print(f"[INFO] Reutilizando Vector Store: {vs_id}")
    else:
        vs = client.vector_stores.create(name=cfg["VECTOR_STORE_NAME"])
        vs_id = vs.id
        _write_vector_store_id(vs_id_file, vs_id)
        print(f"[OK] Vector Store creado: {vs_id}")

    uploaded = 0
    for r in rows:
        pid = r["id"]
        title = (r["title"] or "").strip()
        content = (r["content"] or "").strip()
        if not content:
            continue

        body = (
            f"POST_ID: {pid}\n"
            f"TITLE: {title}\n"
            f"URL:\n"
            f"---\n\n{content}\n"
        )
        buf = io.BytesIO(body.encode("utf-8"))
        filename = f"{pid}_{_slug(title)}.txt"

        f = client.files.create(file=(filename, buf), purpose="assistants")
        client.vector_stores.files.create(vector_store_id=vs_id, file_id=f.id)
        uploaded += 1

    if uploaded == 0:
        raise RuntimeError("Se leyeron posts pero ninguno tenía contenido válido.")

    print(f"[OK] Adjuntados {uploaded} archivos al Vector Store {vs_id}.")
    return vs_id

def chat_with_vector_store(question: str, *, vector_store_id: str, model: str = "gpt-4o-mini") -> str:
    """
    Chat usando Assistants API v2 con file_search y un vector_store dado.
    Crea (o reutiliza) un assistant atado a ese vector store.
    """
    import time
    client = OpenAI()

    # Lee/guarda un assistant_id en instance/assistant_id (para no recrearlo)
    asst_id_file = current_app.config["VECTOR_STORE_ID_FILE"] + "_assistant"
    def _read(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip() or None
        except FileNotFoundError:
            return None
    def _write(path, value):
        with open(path, "w", encoding="utf-8") as f:
            f.write(value.strip())

    assistant_id = _read(asst_id_file)

    instructions = (
        "Eres un chatbot experto en reseñas de licores del sitio. "
        "Responde en español, breve y cita TITLE y POST_ID de la fuente utilizada."
    )

    if not assistant_id:
        # Crea el assistant enlazado al vector store
        asst = client.beta.assistants.create(
            name="Reseñas Licores",
            model=model,
            instructions=instructions,
            tools=[{"type": "file_search"}],
            tool_resources={
                "file_search": {
                    "vector_store_ids": [vector_store_id]
                }
            },
        )
        assistant_id = asst.id
        _write(asst_id_file, assistant_id)
    else:
        # Opcional: asegura que el assistant esté apuntando a tu vector_store (por si cambió)
        client.beta.assistants.update(
            assistant_id=assistant_id,
            model=model,
            instructions=instructions,
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
        )

    # Crea un thread con el mensaje del usuario
    thread = client.beta.threads.create(
        messages=[{"role": "user", "content": question}]
    )

    # Ejecuta el run y hace polling simple hasta que termine
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )

    while run.status in ("queued", "in_progress", "requires_action"):
        time.sleep(0.8)
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

    if run.status != "completed":
        return f"Hubo un problema procesando la respuesta (status: {run.status})."

    # Lee el último mensaje del assistant
    msgs = client.beta.threads.messages.list(thread_id=thread.id, order="desc", limit=1)
    if not msgs.data:
        return "Sin respuesta."
    parts = msgs.data[0].content
    # concatena textos (puede venir en varios 'text' blocks)
    out = []
    for p in parts:
        if p.type == "text":
            out.append(p.text.value)
    return "\n".join(out).strip() or "Sin respuesta."

def get_vector_store_id() -> Optional[str]:
    return _read_vector_store_id(current_app.config["VECTOR_STORE_ID_FILE"])

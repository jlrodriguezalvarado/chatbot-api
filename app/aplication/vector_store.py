# app/aplication/vector_store.py
import io
import os
import re
from typing import Optional, List

from openai import OpenAI
from sqlalchemy import text
from flask import current_app

from app.aplication import db
from app.aplication.models.vector_store_record import VectorStoreRecord

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
    Creates a new Vector Store in OpenAI, uploads all posts, then deletes the previous VS
    (if any) and saves the new id in VectorStoreRecord and in the id file.
    """
    cfg = current_app.config
    if not cfg.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY no configurada")

    client = OpenAI()

    q = f"SELECT id, title, content, product_url FROM {table}"
    if limit:
        q += f" LIMIT {int(limit)}"

    with db_engine.connect() as conn:
        rows = conn.execute(text(q)).mappings().all()

    if not rows:
        raise RuntimeError("No posts found in the table.")

    old_vs_id = get_vector_store_id()

    # Always create a new vector store
    vs = client.vector_stores.create(name=cfg["VECTOR_STORE_NAME"])
    new_vs_id = vs.id
    print(f"[OK] Vector Store created: {new_vs_id}")

    uploaded = 0
    for r in rows:
        pid = r["id"]
        title = (r["title"] or "").strip()
        content = (r["content"] or "").strip()
        product_url = (r.get("product_url") or "").strip()
        if not content:
            continue

        body = (
            f"POST_ID: {pid}\n"
            f"TITLE: {title}\n"
            f"PRODUCT_URL: {product_url}\n"
            f"---\n\n{content}\n"
        )
        buf = io.BytesIO(body.encode("utf-8"))
        filename = f"{pid}_{_slug(title)}.txt"

        f = client.files.create(file=(filename, buf), purpose="assistants")
        client.vector_stores.files.create(vector_store_id=new_vs_id, file_id=f.id)
        uploaded += 1

    if uploaded == 0:
        client.vector_stores.delete(vector_store_id=new_vs_id)
        raise RuntimeError("Se leyeron posts pero ninguno tenía contenido válido.")

    print(f"[OK] Attached {uploaded} files to Vector Store {new_vs_id}.")

    # Delete the previous VS (in OpenAI and local refs) after the new one is ready
    if old_vs_id and old_vs_id != new_vs_id:
        print(f"[INFO] Deleting previous Vector Store: {old_vs_id}")
        delete_vector_store(old_vs_id)
        # Remove old record from DB so only the new one is the "current"
        VectorStoreRecord.query.filter_by(vector_store_id=old_vs_id).delete()
        db.session.commit()

    # Save new VS id in model and file
    record = VectorStoreRecord(vector_store_id=new_vs_id)
    db.session.add(record)
    db.session.commit()
    vs_id_file = cfg["VECTOR_STORE_ID_FILE"]
    _write_vector_store_id(vs_id_file, new_vs_id)
    print(f"[OK] Vector Store {new_vs_id} saved (created_at: {record.created_at}).")
    return new_vs_id

def chat_with_vector_store(question: str, *, vector_store_id: str, model: str = "gpt-4o-mini") -> str:
    """
    Chat using Assistants API v2 with file_search and a given vector_store.
    Create (or reuse) an assistant attached to that vector store.
    """
    import time
    client = OpenAI()

    # Read/save an assistant_id in instance/assistant_id (to not recreate it)
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
        "You are Vinum, an expert sommelier for the website. Your job is to answer questions about the wines and spirits available in the site's catalog using ONLY the information retrieved from the Vector Store (sources). "
        "Language: detect the user's language and ALWAYS respond in that same language. "
        "Source rules (mandatory): do not invent facts and do not use external knowledge. If the answer is not supported by the retrieved sources, reply exactly: 'I can't answer that question.' (in the user's language) and stop. "
        "When citing a source, mention the exact TITLE exactly as it appears in the source (do not alter it). "
        "Answer style: keep responses brief, direct, and useful. Avoid filler. Do not add extra notes, disclaimers, long greetings, or closing comments. Output only the answer text. "
        "Product recommendations: if you recommend a wine/spirit, you MUST ALWAYS include an HTML link using the EXACT PRODUCT_URL provided by the source: <a href=\"PRODUCT_URL\">PRODUCT_NAME</a>. "
        "Never invent URLs, never shorten links, never use partial URLs. The anchor text must be the real product name as shown in the source."
    )


    if not assistant_id:
        # Create the assistant attached to the vector store
        asst = client.beta.assistants.create(
            name="Vinum Sommelier",
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
        # Optional: ensure the assistant is pointing to your vector store (in case it changed)
        client.beta.assistants.update(
            assistant_id=assistant_id,
            model=model,
            instructions=instructions,
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
        )

    # Create a thread with the user's message
    thread = client.beta.threads.create(
        messages=[{"role": "user", "content": question}]
    )

    # Execute the run and do simple polling until it finishes
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )

    while run.status in ("queued", "in_progress", "requires_action"):
        time.sleep(0.8)
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

    if run.status != "completed":
        return f"There was a problem processing the response (status: {run.status})."

    # Read the last message from the assistant
    msgs = client.beta.threads.messages.list(thread_id=thread.id, order="desc", limit=1)
    if not msgs.data:
        return "No response."
    parts = msgs.data[0].content
    # concatenate texts (may come in multiple 'text' blocks)
    out = []
    for p in parts:
        if p.type == "text":
            out.append(p.text.value)
    raw = "\n".join(out).strip() or "No response."
    raw = re.sub(r"【[^】]*】", "", raw)
    return re.sub(r"  +", " ", raw).strip() or "No response."

def get_vector_store_id() -> Optional[str]:
    """Returns the current vector store id from the latest VectorStoreRecord, or from the id file."""
    latest = VectorStoreRecord.query.order_by(VectorStoreRecord.created_at.desc()).first()
    if latest:
        return latest.vector_store_id
    return _read_vector_store_id(current_app.config["VECTOR_STORE_ID_FILE"])


def delete_vector_store(vector_store_id: str) -> None:
    """
    Deletes the vector store in OpenAI, the files associated with it, and local
    files (vector_store_id file and assistant_id file) if they reference this VS.
    """
    if not vector_store_id or not vector_store_id.strip():
        raise ValueError("vector_store_id is required")

    vs_id = vector_store_id.strip()
    cfg = current_app.config
    if not cfg.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not configured")

    client = OpenAI()

    # Collect all file IDs from the vector store (paginated)
    file_ids: List[str] = []
    after = None
    while True:
        list_kw: dict = {"vector_store_id": vs_id, "limit": 100}
        if after:
            list_kw["after"] = after
        page = client.vector_stores.files.list(**list_kw)
        for item in page.data:
            file_ids.append(item.id)
        if not page.has_more:
            break
        if not page.data:
            break
        after = page.data[-1].id

    # Delete the vector store in OpenAI (files may remain in account)
    client.vector_stores.delete(vector_store_id=vs_id)

    # Delete each file from OpenAI
    for fid in file_ids:
        try:
            client.files.delete(file_id=fid)
        except Exception as e:
            # Log but continue; file may already be gone
            print(f"[WARN] Could not delete file {fid}: {e}")

    # Remove local files if they reference this vector store
    vs_id_file = cfg["VECTOR_STORE_ID_FILE"]
    if _read_vector_store_id(vs_id_file) == vs_id:
        try:
            if os.path.isfile(vs_id_file):
                os.remove(vs_id_file)
                print(f"[OK] Removed local file: {vs_id_file}")
        except OSError as e:
            print(f"[WARN] Could not remove {vs_id_file}: {e}")
        asst_file = vs_id_file + "_assistant"
        try:
            if os.path.isfile(asst_file):
                os.remove(asst_file)
                print(f"[OK] Removed local file: {asst_file}")
        except OSError as e:
            print(f"[WARN] Could not remove {asst_file}: {e}")

    print(f"[OK] Vector store {vs_id} and {len(file_ids)} associated file(s) deleted in OpenAI.")

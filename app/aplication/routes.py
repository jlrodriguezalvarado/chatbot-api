import threading

from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import create_engine

from app.aplication.utils.security import require_api_key
from app.aplication.vector_store import chat_with_vector_store, get_vector_store_id, build_vector_store_from_posts
from app.aplication.commands import sync_wordpress_posts

main = Blueprint('main', __name__)


def _run_refresh_in_background(app):
    """Runs sync + build_vs in background. Uses app context for DB/config."""
    with app.app_context():
        try:
            created, updated = sync_wordpress_posts()
            db_url = app.config.get("SQLALCHEMY_DATABASE_URI")
            if db_url:
                engine = create_engine(db_url)
                build_vector_store_from_posts(engine, table="post", limit=None)
                app.logger.info(f"Refresh completed: created={created}, updated={updated}")
        except Exception as e:
            app.logger.exception("Refresh failed: %s", e)

@main.route('/')
def index():
    return 'Access denied', 400

@main.route('/chat', methods=['POST'])
@require_api_key
def chat():
    data = request.get_json(silent=True) or {}
    q = (data.get('q') or '').strip()
    print(f"Question: {q}")
    if not q:
        return jsonify({'error': " 'q' is required"}), 400

    vs_id = override_vs or get_vector_store_id()
    if not vs_id:
        return jsonify({'error': "There is no VECTOR_STORE_ID."}), 400

    answer = chat_with_vector_store(q, vector_store_id=vs_id)
    return jsonify({'answer': answer})
    
@main.route('/chat/refresh-chatbot-knowledge', methods=['POST'])
@require_api_key
def refresh_chatbot_knowledge():
    db_url = current_app.config.get("SQLALCHEMY_DATABASE_URI")
    if not db_url:
        return jsonify({'error': "SQLALCHEMY_DATABASE_URI is not configured"}), 400

    app = current_app._get_current_object()
    t = threading.Thread(target=_run_refresh_in_background, args=(app,))
    t.daemon = True
    t.start()

    return jsonify({
        'message': 'The chat will be refreshed in the background. The knowledge will be updated in a few minutes.',
        'status': 'started'
    }), 202
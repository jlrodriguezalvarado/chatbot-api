from flask import Blueprint, jsonify, request, current_app
from app.aplication.utils.security import require_api_key

from app.aplication.vector_store import chat_with_vector_store, get_vector_store_id

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return jsonify({'message': 'Welcome to the API!'})

@main.route('/protected')
@require_api_key
def protected():
    return jsonify({'message': 'This is a protected route. now and forever'})

@main.route('/chat', methods=['POST'])
@require_api_key                 # quítalo si quieres público
def chat():
    data = request.get_json(silent=True) or {}
    q = (data.get('q') or '').strip()
    print(f"Question: {q}")
    if not q:
        return jsonify({'error': "Falta 'q'"}), 400

    override_vs = (data.get('vector_store_id') or '').strip()
    vs_id = override_vs or get_vector_store_id()
    if not vs_id:
        return jsonify({'error': "No hay VECTOR_STORE_ID. Ejecuta 'flask build_vs' antes."}), 400

    answer = chat_with_vector_store(q, vector_store_id=vs_id)
    return jsonify({'answer': answer})
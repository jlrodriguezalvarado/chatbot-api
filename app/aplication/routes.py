from flask import Blueprint, jsonify
from app.aplication.utils.security import require_api_key

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return jsonify({'message': 'Welcome to the API!'})

@main.route('/protected')
@require_api_key
def protected():
    return jsonify({'message': 'This is a protected route.'})

from functools import wraps
from flask import request, jsonify
from app.aplication.models.apikey import ApiKey

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'message': 'Authorization header is missing or invalid'}), 401

        api_key = auth_header.split(' ')[1]
        if not api_key:
            return jsonify({'message': 'API key is missing'}), 401

        key = ApiKey.query.filter_by(key=api_key).first()
        if not key:
            return jsonify({'message': 'Invalid API key'}), 401

        return f(*args, **kwargs)
    return decorated_function

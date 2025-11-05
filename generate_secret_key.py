#!/usr/bin/env python3
"""
Script para generar un SECRET_KEY seguro para Flask.
Uso: python generate_secret_key.py
"""
import secrets
import sys

def generate_secret_key():
    """Genera un SECRET_KEY seguro usando secrets.token_hex"""
    return secrets.token_hex(32)

if __name__ == '__main__':
    secret_key = generate_secret_key()
    print(f"SECRET_KEY={secret_key}")
    print("\nCopia esta línea a tu archivo .env:")
    print(f"SECRET_KEY={secret_key}")


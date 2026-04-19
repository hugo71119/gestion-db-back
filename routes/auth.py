from flask import Blueprint, request, jsonify, session
from flask_jwt_extended import create_access_token
import pyodbc
from config import CONNECTION_STRING

auth_bp = Blueprint('auth', __name__)

def get_conn():
    return pyodbc.connect(CONNECTION_STRING)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    tipo       = data.get('tipo', '')
    usuario    = data.get('usuario', '')
    contrasena = data.get('contrasena', '')

    if not tipo or not usuario or not contrasena:
        return jsonify({'error': 'Faltan campos'}), 400

    if tipo == 'admin':
        if usuario == 'admin' and contrasena == 'Admin2024!':
            session['usuario'] = usuario
            session['rol']     = 'admin'
            return jsonify({'mensaje': 'Login exitoso', 'rol': 'admin', 'nombre': 'Administrador'})
        return jsonify({'error': 'Credenciales incorrectas'}), 401

    try:
        conn   = get_conn()
        cursor = conn.cursor()

        if tipo == 'repartidor':
            cursor.execute('EXEC sp_login_repartidor ?, ?', usuario, contrasena)
            row = cursor.fetchone()
            if row:
                session['usuario']       = usuario
                session['rol']           = 'repartidor'
                session['repartidor_id'] = row[0]
                return jsonify({
                    'mensaje':       'Login exitoso',
                    'rol':           'repartidor',
                    'repartidor_id': row[0],
                    'nombre':        row[1]
                })
            return jsonify({'error': 'Credenciales incorrectas'}), 401

        elif tipo == 'cliente':
            cursor.execute(
                'SELECT cliente_id, nombre_completo, email FROM Clientes WHERE email = ?',
                usuario
            )
            row = cursor.fetchone()
            if row:
                cliente_id = row[0]
                nombre     = row[1]

                # Sesión web
                session['usuario']    = usuario
                session['rol']        = 'cliente'
                session['cliente_id'] = cliente_id

                # JWT para el agente n8n / ElevenLabs
                access_token = create_access_token(
                identity=str(cliente_id),
                additional_claims={
                    'cliente_id': cliente_id,
                    'rol': 'cliente',
                    'nombre': nombre
                })
            
                return jsonify({
                    'mensaje':      'Login exitoso',
                    'rol':          'cliente',
                    'cliente_id':   cliente_id,
                    'nombre':       nombre,
                    'access_token': access_token
                })
            return jsonify({'error': 'Cliente no encontrado'}), 401

        return jsonify({'error': 'Tipo de usuario invalido'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'mensaje': 'Sesion cerrada'})

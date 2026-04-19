from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import pyodbc
from config import CONNECTION_STRING

agente_bp = Blueprint('agente', __name__)

def get_conn():
    return pyodbc.connect(CONNECTION_STRING)

def row_to_dict(cursor, row):
    return dict(zip([col[0] for col in cursor.description], row))

def cliente_actual():
    identity = get_jwt_identity()
    return int(identity)


@agente_bp.route('/pedidos/<int:pedido_id>/rastrear', methods=['GET'])
@jwt_required()
def rastrear_pedido(pedido_id):
    """
    Devuelve el estado actual del pedido con información del repartidor
    y vehículo asignado, pensado para respuesta del agente de voz.
    """
    cliente_id = cliente_actual()
    try:
        conn   = get_conn()
        cursor = conn.cursor()

        # Verificar que el pedido pertenece al cliente
        cursor.execute(
            'SELECT pedido_id, estado, direccion_entrega, total, fecha_pedido '
            'FROM Pedidos WHERE pedido_id = ? AND cliente_id = ?',
            pedido_id, cliente_id
        )
        pedido = cursor.fetchone()
        if not pedido:
            return jsonify({'error': 'Pedido no encontrado o no autorizado'}), 404

        resultado = row_to_dict(cursor, pedido)

        # Buscar entrega asignada
        cursor.execute(
            'SELECT e.estado AS estado_entrega, e.fecha_salida, e.fecha_entrega, '
            'r.nombre_completo AS repartidor, r.telefono AS telefono_repartidor, '
            'v.tipo AS vehiculo, v.placa '
            'FROM Entregas e '
            'JOIN Repartidores r ON e.repartidor_id = r.repartidor_id '
            'JOIN Vehiculos v    ON e.vehiculo_id   = v.vehiculo_id '
            'WHERE e.pedido_id = ?',
            pedido_id
        )
        entrega = cursor.fetchone()
        if entrega:
            resultado['entrega'] = row_to_dict(cursor, entrega)
        else:
            resultado['entrega'] = None

        # Mensaje amigable para el agente de voz
        estado = resultado['estado']
        if estado == 'Pendiente':
            resultado['mensaje_voz'] = 'Tu pedido está pendiente de ser aceptado por el administrador.'
        elif estado == 'En ruta':
            rep = resultado['entrega']['repartidor'] if resultado['entrega'] else 'un repartidor'
            resultado['mensaje_voz'] = f'Tu pedido ya va en camino. Lo lleva {rep}.'
        elif estado == 'Entregado':
            resultado['mensaje_voz'] = 'Tu pedido ya fue entregado. ¡Gracias por tu compra!'
        elif estado == 'Cancelado':
            resultado['mensaje_voz'] = 'Este pedido fue cancelado.'

        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agente_bp.route('/pedidos/<int:pedido_id>/cancelar', methods=['POST'])
@jwt_required()
def cancelar_pedido(pedido_id):
    """
    Cancela un pedido únicamente si su estado es 'Pendiente'
    (el admin aún no lo ha aceptado).
    """
    cliente_id = cliente_actual()
    try:
        conn   = get_conn()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT estado FROM Pedidos WHERE pedido_id = ? AND cliente_id = ?',
            pedido_id, cliente_id
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Pedido no encontrado o no autorizado'}), 404

        estado_actual = row[0]
        if estado_actual != 'Pendiente':
            return jsonify({
                'error': f'No se puede cancelar. El pedido ya está en estado "{estado_actual}".',
                'mensaje_voz': f'Lo siento, tu pedido no se puede cancelar porque ya está en estado {estado_actual}.'
            }), 400

        cursor.execute(
            "UPDATE Pedidos SET estado = 'Cancelado' WHERE pedido_id = ?",
            pedido_id
        )
        conn.commit()
        return jsonify({
            'mensaje': 'Pedido cancelado exitosamente',
            'mensaje_voz': 'Tu pedido ha sido cancelado sin problema.'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agente_bp.route('/pedidos/repetir', methods=['POST'])
@jwt_required()
def repetir_ultimo_pedido():
    """
    Clona el último pedido del cliente (productos y dirección)
    creando uno nuevo en estado Pendiente.
    Acepta opcionalmente una nueva dirección_entrega en el body.
    """
    cliente_id = cliente_actual()
    data = request.get_json() or {}
    try:
        conn   = get_conn()
        cursor = conn.cursor()

        # Obtener el último pedido del cliente
        cursor.execute(
            'SELECT TOP 1 pedido_id, direccion_entrega '
            'FROM Pedidos WHERE cliente_id = ? AND estado != ? '
            'ORDER BY fecha_pedido DESC',
            cliente_id, 'Cancelado'
        )
        ultimo = cursor.fetchone()
        if not ultimo:
            return jsonify({
                'error': 'No tienes pedidos anteriores para repetir',
                'mensaje_voz': 'No encontré pedidos anteriores en tu cuenta.'
            }), 404

        pedido_origen_id   = ultimo[0]
        direccion_original = ultimo[1]
        nueva_direccion    = data.get('direccion_entrega', direccion_original)

        # Obtener detalles del pedido original
        cursor.execute(
            'SELECT producto, cantidad, precio_unitario FROM Detalle_Pedidos WHERE pedido_id = ?',
            pedido_origen_id
        )
        detalles = cursor.fetchall()
        if not detalles:
            return jsonify({'error': 'El pedido original no tiene productos'}), 400

        # Crear el nuevo pedido
        cursor.execute('EXEC sp_generar_pedido ?, ?', cliente_id, nueva_direccion)
        nuevo_id = None
        while True:
            if cursor.description is not None:
                nuevo_id = cursor.fetchone()[0]
                break
            if not cursor.nextset():
                break

        # Copiar detalles
        for det in detalles:
            cursor.execute(
                'INSERT INTO Detalle_Pedidos (pedido_id, producto, cantidad, precio_unitario) '
                'VALUES (?, ?, ?, ?)',
                nuevo_id, det[0], det[1], det[2]
            )

        cursor.execute(
            'UPDATE Pedidos SET total = '
            '(SELECT SUM(subtotal) FROM Detalle_Pedidos WHERE pedido_id = ?) '
            'WHERE pedido_id = ?',
            nuevo_id, nuevo_id
        )
        conn.commit()

        return jsonify({
            'mensaje':      'Pedido repetido exitosamente',
            'pedido_id':    nuevo_id,
            'direccion':    nueva_direccion,
            'mensaje_voz':  f'Listo, creé un nuevo pedido igual al anterior. '
                            f'El número de tu pedido es {nuevo_id}.'
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agente_bp.route('/pedidos/<int:pedido_id>/direccion', methods=['PUT'])
@jwt_required()
def cambiar_direccion(pedido_id):
    """
    Cambia la dirección de entrega de un pedido solo si
    su estado es 'Pendiente'.
    """
    cliente_id = cliente_actual()
    data = request.get_json()
    nueva_direccion = data.get('direccion_entrega', '').strip()

    if not nueva_direccion:
        return jsonify({'error': 'Debe proporcionar una dirección'}), 400

    try:
        conn   = get_conn()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT estado FROM Pedidos WHERE pedido_id = ? AND cliente_id = ?',
            pedido_id, cliente_id
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Pedido no encontrado o no autorizado'}), 404

        if row[0] != 'Pendiente':
            return jsonify({
                'error': f'No se puede cambiar la dirección. El pedido está en estado "{row[0]}".',
                'mensaje_voz': f'No puedo cambiar la dirección porque tu pedido ya está {row[0]}.'
            }), 400

        cursor.execute(
            'UPDATE Pedidos SET direccion_entrega = ? WHERE pedido_id = ?',
            nueva_direccion, pedido_id
        )
        conn.commit()
        return jsonify({
            'mensaje':     'Dirección actualizada',
            'mensaje_voz': f'Listo, la dirección de entrega fue actualizada a: {nueva_direccion}.'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agente_bp.route('/pedidos/<int:pedido_id>/historial', methods=['GET'])
@jwt_required()
def historial_pedido(pedido_id):
    """
    Devuelve el historial de cambios de estado del pedido
    desde la tabla Auditoria_Pedidos.
    """
    cliente_id = cliente_actual()
    try:
        conn   = get_conn()
        cursor = conn.cursor()

        # Verificar propiedad
        cursor.execute(
            'SELECT pedido_id FROM Pedidos WHERE pedido_id = ? AND cliente_id = ?',
            pedido_id, cliente_id
        )
        if not cursor.fetchone():
            return jsonify({'error': 'Pedido no encontrado o no autorizado'}), 404

        cursor.execute(
            'SELECT estado_anterior, estado_nuevo, fecha, usuario_db '
            'FROM Auditoria_Pedidos WHERE pedido_id = ? ORDER BY fecha ASC',
            pedido_id
        )
        rows = cursor.fetchall()
        historial = [row_to_dict(cursor, r) for r in rows]

        mensaje_voz = 'Tu pedido pasó por los siguientes estados: '
        mensaje_voz += ', luego '.join(
            [f"{h.get('estado_anterior','inicio')} a {h['estado_nuevo']}" for h in historial]
        ) if historial else 'sin cambios registrados.'

        return jsonify({'historial': historial, 'mensaje_voz': mensaje_voz})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agente_bp.route('/resumen', methods=['GET'])
@jwt_required()
def resumen_cliente():
    """
    Resumen de actividad del cliente autenticado:
    pedidos por estado, total gastado y últimos 5 pedidos.
    """
    cliente_id = cliente_actual()
    try:
        conn   = get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM Pedidos WHERE cliente_id = ? AND estado = 'Pendiente'", cliente_id)
        pendientes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Pedidos WHERE cliente_id = ? AND estado = 'En ruta'", cliente_id)
        en_ruta = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM Pedidos WHERE cliente_id = ? AND estado = 'Entregado'", cliente_id)
        entregados = cursor.fetchone()[0]

        cursor.execute("SELECT ISNULL(SUM(total), 0) FROM Pedidos WHERE cliente_id = ?", cliente_id)
        total_gastado = float(cursor.fetchone()[0])

        cursor.execute(
            'SELECT TOP 5 pedido_id, direccion_entrega, estado, total, fecha_pedido '
            'FROM Pedidos WHERE cliente_id = ? ORDER BY fecha_pedido DESC',
            cliente_id
        )
        recientes = [row_to_dict(cursor, r) for r in cursor.fetchall()]

        return jsonify({
            'pendientes':    pendientes,
            'en_ruta':       en_ruta,
            'entregados':    entregados,
            'total_gastado': total_gastado,
            'recientes':     recientes,
            'mensaje_voz':   f'Has gastado un total de {total_gastado:.2f} pesos. '
                             f'Tienes {pendientes} pedidos pendientes y {en_ruta} en camino.'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agente_bp.route('/pedidos', methods=['POST'])
@jwt_required()
def crear_pedido():
    """
    Crea un pedido nuevo para el cliente autenticado.
    El cliente_id se toma del JWT — no se puede suplantar.
    """
    cliente_id = cliente_actual()
    data = request.get_json()
    try:
        conn   = get_conn()
        cursor = conn.cursor()

        cursor.execute('EXEC sp_generar_pedido ?, ?', cliente_id, data['direccion_entrega'])
        nuevo_id = None
        while True:
            if cursor.description is not None:
                nuevo_id = cursor.fetchone()[0]
                break
            if not cursor.nextset():
                break

        if nuevo_id and data.get('detalles'):
            for det in data['detalles']:
                cursor.execute(
                    'INSERT INTO Detalle_Pedidos (pedido_id, producto, cantidad, precio_unitario) '
                    'VALUES (?, ?, ?, ?)',
                    nuevo_id, det['producto'], det['cantidad'], det['precio_unitario']
                )
            cursor.execute(
                'UPDATE Pedidos SET total = '
                '(SELECT SUM(subtotal) FROM Detalle_Pedidos WHERE pedido_id = ?) '
                'WHERE pedido_id = ?',
                nuevo_id, nuevo_id
            )

        conn.commit()
        return jsonify({
            'mensaje':     'Pedido creado',
            'pedido_id':   nuevo_id,
            'mensaje_voz': f'Tu pedido fue creado exitosamente. El número de seguimiento es {nuevo_id}.'
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

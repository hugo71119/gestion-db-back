from flask import Flask
from flask_cors import CORS
from config import SECRET_KEY

from routes.auth         import auth_bp
from routes.clientes     import clientes_bp
from routes.pedidos      import pedidos_bp
from routes.entregas     import entregas_bp
from routes.repartidores import repartidores_bp
from routes.vehiculos    import vehiculos_bp
from routes.pagos        import pagos_bp
from routes.reportes     import reportes_bp

app = Flask(__name__)
app.secret_key = SECRET_KEY

CORS(app, supports_credentials=True, origins=['http://localhost:3000', 'http://localhost'])

app.register_blueprint(auth_bp,         url_prefix='/api/auth')
app.register_blueprint(clientes_bp,     url_prefix='/api/clientes')
app.register_blueprint(pedidos_bp,      url_prefix='/api/pedidos')
app.register_blueprint(entregas_bp,     url_prefix='/api/entregas')
app.register_blueprint(repartidores_bp, url_prefix='/api/repartidores')
app.register_blueprint(vehiculos_bp,    url_prefix='/api/vehiculos')
app.register_blueprint(pagos_bp,        url_prefix='/api/pagos')
app.register_blueprint(reportes_bp,     url_prefix='/api/reportes')

@app.route('/api/health')
def health():
    return {'status': 'ok', 'mensaje': 'Sistema de Logistica API funcionando'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)

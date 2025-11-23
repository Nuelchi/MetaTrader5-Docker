import logging
import os
from flask import Flask
from dotenv import load_dotenv
from flasgger import Swagger
from werkzeug.middleware.proxy_fix import ProxyFix
from swagger import swagger_config

# Import routes
from routes.health import health_bp
from routes.login import login_bp
from routes.symbol import symbol_bp
from routes.data import data_bp
from routes.position import position_bp
from routes.order import order_bp
from routes.history import history_bp
from routes.error import error_bp

load_dotenv()
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['PREFERRED_URL_SCHEME'] = 'https'

swagger = Swagger(app, config=swagger_config)

# Register blueprints
app.register_blueprint(health_bp)
app.register_blueprint(login_bp)
app.register_blueprint(symbol_bp)
app.register_blueprint(data_bp)
app.register_blueprint(position_bp)
app.register_blueprint(order_bp)
app.register_blueprint(history_bp)
app.register_blueprint(error_bp)

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Global MT5 instance
mt5 = None

if __name__ == '__main__':
    # Try to connect to mt5linux server first
    try:
        from mt5linux import MetaTrader5 as MT5Linux
        global mt5
        mt5 = MT5Linux(host='localhost', port=8001)
        logger.info("Connected to mt5linux server successfully.")
    except Exception as e:
        logger.error(f"Failed to connect to mt5linux server: {e}")
        # Fallback to direct MT5 initialization if mt5linux fails
        try:
            import MetaTrader5 as MT5Direct
            global mt5
            mt5 = MT5Direct
            if not mt5.initialize():
                logger.error("Failed to initialize MT5 directly.")
        except ImportError:
            logger.error("MetaTrader5 library not available for fallback.")

    app.run(host='0.0.0.0', port=int(os.environ.get('MT5_API_PORT')))
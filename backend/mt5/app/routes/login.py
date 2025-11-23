from flask import Blueprint, jsonify, request
import MetaTrader5 as mt5
import logging
from flasgger import swag_from

login_bp = Blueprint('login', __name__)
logger = logging.getLogger(__name__)

@login_bp.route('/login', methods=['POST'])
@swag_from({
    'tags': ['Authentication'],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'login': {'type': 'integer'},
                    'password': {'type': 'string'},
                    'server': {'type': 'string'}
                },
                'required': ['login', 'password', 'server']
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Login successful',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'account_info': {
                        'type': 'object',
                        'properties': {
                            'login': {'type': 'integer'},
                            'server': {'type': 'string'},
                            'balance': {'type': 'number'},
                            'equity': {'type': 'number'}
                        }
                    }
                }
            }
        },
        400: {
            'description': 'Login failed'
        }
    }
})
def login():
    """
    Login to MT5 Account
    ---
    description: Authenticate with MT5 account credentials
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Login data is required"}), 400

        required_fields = ['login', 'password', 'server']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields: login, password, server"}), 400

        # Perform login
        login_result = mt5.login(
            login=int(data['login']),
            password=data['password'],
            server=data['server']
        )

        if not login_result:
            error = mt5.last_error()
            logger.error(f"MT5 login failed: {error}")
            return jsonify({
                "error": f"Login failed: {error}",
                "mt5_error": str(error)
            }), 400

        # Get account info to verify login
        account_info = mt5.account_info()
        if not account_info:
            return jsonify({"error": "Login succeeded but failed to get account info"}), 400

        logger.info(f"MT5 login successful for account {data['login']}")

        return jsonify({
            "message": "Login successful",
            "account_info": {
                "login": account_info.login,
                "server": account_info.server,
                "balance": float(account_info.balance),
                "equity": float(account_info.equity),
                "currency": account_info.currency
            }
        }), 200

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
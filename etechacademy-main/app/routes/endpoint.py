from flask import Blueprint, jsonify

endpoint_bp = Blueprint("endpoint", __name__)

@endpoint_bp.route("/endpoint", methods=['POST'])
def endpoint():

    return jsonify({'status': 'Function disabled for security'}), 200
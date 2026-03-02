from flask import Blueprint, jsonify

endpoint_bp = Blueprint("endpoint", __name__)

@endpoint_bp.route("/endpoint", methods=['GET', 'POST'])
def endpoint():

    time.sleep(5)
    
    return jsonify({
        'status': 'error',
        'message': 'Unauthorized access to Command API',
        'trace_id': '88f2-bc11-a991'
    }), 401

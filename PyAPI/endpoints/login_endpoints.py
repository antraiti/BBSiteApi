from flask import request, jsonify, make_response
import datetime, jwt
from werkzeug.security import check_password_hash
from models import User
from main import app, limiter

@app.route('/login', methods=['POST'])
@limiter.limit("10/hour", override_defaults=False)
def login():
    data = request.get_json()
    print(data)
    if not data or not data['username'] or not data['password']:
        return make_response('Could not verify', 401, {'WWW-authenticate' : 'Basic realm="Login Required"'})

    user = User.query.filter_by(username=data['username']).first()
    if not user:
        return jsonify('Could not verify', 401, {'WWW-authenticate' : 'Basic realm="Login Required"'})
    
    if check_password_hash(user.hash, data['password']):
        token = jwt.encode({'username': user.username, 'uid': user.id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=31), 'version': app.config['API_VERSION']}, app.config['SECRET_KEY'])
        return jsonify({'token': token, 'username': user.username, 'id': user.id, 'isadmin': user.admin})
    
    return jsonify('Could not verify' + user.hash + data['password'], 401, {'WWW-authenticate' : 'Basic realm="Login Required"'})

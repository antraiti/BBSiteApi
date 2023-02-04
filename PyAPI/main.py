from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import jwt
import datetime
import configparser
from functools import wraps

app = Flask(__name__)
config = configparser.ConfigParser()
config.read('config.ini')

app.config['SECRET_KEY'] = ''
app.config['SQLALCHEMY_DATABASE_URI'] = ''

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    publicid = db.Column(db.String(50), unique=True)
    username = db.Column(db.String(32), unique=True)
    hash = db.Column(db.String(255))
    salt = db.Column(db.String(255))
    admin = db.Column(db.Boolean)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

        if not token:
            return jsonify({'message' : 'Token is missing!'}), 401
        try: 
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.filter_by(publicid=data['publicid']).first()
        except:
            return jsonify({'message' : 'Token is invalid!'}), 401

        return f(current_user, *args, **kwargs)

    return decorated

@app.route('/user', methods=['POST'])
@token_required
def create_user(current_user):
    data = request.get_json()
    print(data['username'])
    user = User.query.filter_by(username=data['username']).first()

    if user:
        return jsonify({'message' : 'User already exists'})

    hashed_password = generate_password_hash(data['password'])

    new_user = User(username=data['username'], hash=hashed_password, publicid=str(uuid.uuid4()))
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message' : 'New user created'})

@app.route('/user/<username>', methods=['PUT'])
@token_required
def update_user(current_user, username):
    data = request.get_json()

    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify({'message' : 'No user found!'})

    user.salt = "yoyo"
    db.session.commit()

    return jsonify({'message' : 'Updated user'})

@app.route('/login')
def login():
    auth = request.authorization

    if not auth or not auth.username or not auth.password:
        return make_response('Could not verify', 401, {'WWW-authenticate' : 'Basic realm="Login Required"'})
    
    user = User.query.filter_by(username=auth.username).first()

    if not user:
        return jsonify('Could not verify', 401, {'WWW-authenticate' : 'Basic realm="Login Required"'})

    if check_password_hash(user.hash, auth.password):
        token = jwt.encode({'username': user.username, 'publicid':user.publicid, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60)}, app.config['SECRET_KEY'])
        return jsonify({'token': token})

    return jsonify('Could not verify' + user.hash + auth.password, 401, {'WWW-authenticate' : 'Basic realm="Login Required"'})

if __name__ == "__main__":
    app.run(debug=True)


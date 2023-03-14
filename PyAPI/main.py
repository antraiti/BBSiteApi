from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
import uuid
import jwt
import datetime
import configparser
from functools import wraps

app = Flask(__name__)
CORS(app)
config = configparser.ConfigParser()
config.read(Path(__file__).with_name('config.ini'))

app.config['SECRET_KEY'] = config['SECURITY']['SECRET_KEY']
app.config['SQLALCHEMY_DATABASE_URI'] = config['DATABASE']['CONNECTION']

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    publicid = db.Column(db.String(50), unique=True)
    username = db.Column(db.String(32), unique=True)
    hash = db.Column(db.String(255))
    salt = db.Column(db.String(255))
    admin = db.Column(db.Boolean)

class Userdeck(db.Model):
    userid = db.Column(db.Integer, db.ForeignKey('user.id'))
    deckid = db.Column(db.Integer, db.ForeignKey('deck.id'))

class Deck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    link = db.Column(db.String(255))
    lastused = db.Column(db.DateTime)
    commander = db.Column(db.String(64))
    partner = db.Column(db.String(64))
    companion = db.Column(db.String(64))
    power = db.Column(db.Integer)
    identityid = db.Column(db.Integer, db.ForeignKey('coloridentity.id'))

class Coloridentity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(16), uniqe=True)
    blue = db.Column(db.Boolean)
    white = db.Column(db.Boolean)
    green = db.Column(db.Boolean)
    red = db.Column(db.Boolean)
    black = db.Column(db.Boolean)


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

###############################################
# User
###############################################
@app.route('/user', methods=['POST'])
@token_required
def create_user(current_user):
    if not current_user.admin:
        return jsonify({'message' : 'Lacking Permissions'})

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
    if not current_user.admin:
        return jsonify({'message' : 'Lacking Permissions'})

    data = request.get_json()

    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify({'message' : 'No user found!'})

    user.salt = "yoyo"
    db.session.commit()

    return jsonify({'message' : 'Updated user'})


###############################################
# Deck
###############################################
@app.route('/deck', methods=['POST'])
@token_required
def create_deck(current_user):
    data = request.get_json()

    new_deck = Deck(name=data['name'], link=data['link'], commander=data['commander'], partner=data['partner'], companion=data['companion'], power=data['power'], identityid=data['identityid'])
    print(new_deck.id)
    new_userdeck = Userdeck(userid=current_user.id, deckid=new_deck.id)
    db.session.add(new_deck)
    db.session.add(new_userdeck)
    db.session.commit()

    return jsonify({'message' : 'New deck created'})

@app.route('/user/<deckid>', methods=['PUT'])
@token_required
def update_user(current_user, deckid):
    if not current_user.admin:
        return jsonify({'message' : 'Lacking Permissions'})
    
    data = request.get_json()
    deck = Deck.query.filter_by(id=deckid).first()
    if not deck:
        return jsonify({'message' : 'No deck found!'})
    
    if data['name']:
        deck.name = data['name']

    db.session.commit()
    return jsonify({'message' : 'Updated user'})


###############################################
# Login
###############################################
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data['username'] or not data['password']:
        return make_response('Could not verify', 401, {'WWW-authenticate' : 'Basic realm="Login Required"'})
    
    user = User.query.filter_by(username=data['username']).first()
    if not user:
        return jsonify('Could not verify', 401, {'WWW-authenticate' : 'Basic realm="Login Required"'})

    if check_password_hash(user.hash, data['password']):
        token = jwt.encode({'username': user.username, 'publicid':user.publicid, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60)}, app.config['SECRET_KEY'])
        return jsonify({'token': token, 'username': user.username}) #TODO: Define a model for the response data

    return jsonify('Could not verify' + user.hash + data['password'], 401, {'WWW-authenticate' : 'Basic realm="Login Required"'})

if __name__ == "__main__":
    app.run(debug=True)


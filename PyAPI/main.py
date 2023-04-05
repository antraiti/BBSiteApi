from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
import uuid
import jwt
import datetime
import configparser
from dataclasses import dataclass
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

@dataclass
class Deck(db.Model):
    id: int
    name: str
    link: str
    lastused: datetime
    commander: str
    partner: str
    companion: str
    power: int
    identityid: int

    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer)
    name = db.Column(db.String(64))
    link = db.Column(db.String(255))
    lastused = db.Column(db.DateTime)
    commander = db.Column(db.String(64))
    partner = db.Column(db.String(64))
    companion = db.Column(db.String(64))
    power = db.Column(db.Integer)
    identityid = db.Column(db.Integer, db.ForeignKey('coloridentity.id'))

@dataclass
class Coloridentity(db.Model):
    id: int
    name: str
    blue: bool
    white: bool
    green: bool
    red: bool
    black: bool

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(16), unique=True)
    blue = db.Column(db.Boolean)
    white = db.Column(db.Boolean)
    green = db.Column(db.Boolean)
    red = db.Column(db.Boolean)
    black = db.Column(db.Boolean)

@dataclass
class Event(db.Model):
    id: int
    name: str
    time: datetime
    themed: bool
    themeid: int

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    time = db.Column(db.DateTime)
    themed = db.Column(db.Boolean)
    themeid = db.Column(db.Integer)

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

    #Handle changes here

    db.session.commit()

    return jsonify({'message' : 'Updated user'})


###############################################
# Deck
###############################################
@app.route('/deck', methods=['POST'])
@token_required
def create_deck(current_user):
    data = request.get_json()
    name = 'New Deck'
    link = ''
    commander = ''
    partner = ''
    companion = ''
    power = 0
    cidentity = 1

    if 'name' in data:
        name = data['name']
    if 'link' in data:
        name = data['link']
    if 'commander' in data:
        name = data['commander']
    if 'partner' in data:
        name = data['partner']
    if 'companion' in data:
        name = data['companion']
    if 'power' in data:
        name = data['power']
    if 'cidentity' in data:
        name = data['cidentity']

    new_deck = Deck(userid=current_user.id, name=name, link=link, commander=commander, partner=partner, companion=companion, power=power, identityid=cidentity)
    db.session.add(new_deck)
    db.session.commit()

    return jsonify({'message' : 'New deck created'})

@app.route('/deck', methods=['PUT'])
@token_required
def update_deck(current_user):
    data = request.get_json()
    
    deck = Deck.query.filter_by(id=data['id']).first()
    if not deck:
        return jsonify({'message' : 'No deck found!'})
    
    if 'name' in data:
        deck.name = data['name']
    if 'link' in data:
        deck.link = data['link']
    if 'commander' in data:
        deck.commander = data['commander']
    if 'partner' in data:
        deck.partner = data['partner']
    if 'companion' in data:
        deck.companion = data['companion']
    if 'power' in data:
        deck.power = data['power']
    if 'identityid' in data:
        deck.identityid = data['identityid']

    db.session.commit()
    return jsonify({'message' : 'Updated deck'})

@app.route('/deck', methods=['GET'])
@token_required
def get_user_decks(current_user):
    decks = Deck.query.filter_by(userid=current_user.id).all()
    if not decks:
        return jsonify({'message' : 'No decks found!'}), 204
    
    return jsonify(decks)

###############################################
# Events
###############################################
@app.route('/event', methods=['POST'])
@token_required
def create_event(current_user):
    data = request.get_json()
    name = 'New Untitled Event ' +   datetime.date.today().strftime("%m/%d")
    time = datetime.datetime.now()
    themed = False

    new_event = Event(name=name, time=time, themed=themed)
    db.session.add(new_event)
    db.session.commit()

    return jsonify({'message' : 'New event created'})

@app.route('/event', methods=['PUT'])
@token_required
def update_event(current_user):
    data = request.get_json()
    
    event = Event.query.filter_by(id=data['id']).first()
    if not event:
        return jsonify({'message' : 'No event found!'})
    
    if 'name' in event:
        event.name = data['name']
    if 'time' in data:
        event.time = data['time']
    if 'themed' in data:
        event.themed = data['themed']
    if 'themeid' in data:
        event.themeid = data['themeid']

    db.session.commit()
    return jsonify({'message' : 'Updated event'})

@app.route('/event', methods=['GET'])
@token_required
def get_events(current_user):
    events = Event.query.all()
    if not events:
        return jsonify({'message' : 'No events found!'}), 204
    
    return jsonify(events)


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
        token = jwt.encode({'username': user.username, 'publicid':user.publicid, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)}, app.config['SECRET_KEY'])
        return jsonify({'token': token, 'username': user.username}) #TODO: Define a model for the response data

    return jsonify('Could not verify' + user.hash + data['password'], 401, {'WWW-authenticate' : 'Basic realm="Login Required"'})


###############################################
# Util
###############################################
@app.route('/colors', methods=['GET'])
def get_coloridentities():
    colors = Coloridentity.query.all()
    return jsonify(colors)

if __name__ == "__main__":
    app.run(debug=True)


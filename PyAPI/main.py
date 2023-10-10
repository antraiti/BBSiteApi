from flask import Flask, request, jsonify, make_response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
from sqlalchemy.orm import aliased
import uuid
import jwt
import re
import datetime
import time
import configparser
import requests
import json
from dataclasses import dataclass
from functools import wraps
from sqlalchemy import delete

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["60 per minute"], #this should be reduced as we optimize the pages (10 per min probably with an added hour or day amount cap)
    storage_uri="memory://",
)

CORS(app)
config = configparser.ConfigParser()
config.read(Path(__file__).with_name('config.ini'))

app.config['SECRET_KEY'] = config['SECURITY']['SECRET_KEY']
app.config['SQLALCHEMY_DATABASE_URI'] = config['DATABASE']['CONNECTION']

db = SQLAlchemy(app)

#DECKLINE_REGEX = r'(\d+x?)?\s*([^(\n]+)'
DECKLINE_REGEX = r'^(\d+x?)?\s*([^(\n\*]+)\s*(?:\(.*\))?\s*(\*CMDR\*)?'

@dataclass
class User(db.Model):
    publicid: int
    username: str
    admin: bool

    id = db.Column(db.Integer, primary_key=True)
    publicid = db.Column(db.String(50), unique=True)
    username = db.Column(db.String(32), unique=True)
    hash = db.Column(db.String(255))
    salt = db.Column(db.String(255))
    admin = db.Column(db.Boolean)

@dataclass
class Card(db.Model):
    id: int
    name: str
    mv: int
    cost: str
    identityid: int
    banned: bool
    watchlist: bool

    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(64))
    mv = db.Column(db.Integer)
    cost = db.Column(db.String(64))
    identityid = db.Column(db.Integer, db.ForeignKey('coloridentity.id'))
    banned = db.Column(db.Boolean)
    watchlist = db.Column(db.Boolean)

@dataclass
class Deck(db.Model):
    id: int
    userid: int
    name: str
    lastused: datetime
    commander: Card
    partner: Card
    companion: Card
    power: int
    identityid: int
    lastupdated: datetime

    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(64))
    lastused = db.Column(db.DateTime)
    commander = db.Column(db.String(36), db.ForeignKey('card.id'))
    partner = db.Column(db.String(36), db.ForeignKey('card.id'))
    companion = db.Column(db.String(36), db.ForeignKey('card.id'))
    power = db.Column(db.Integer)
    identityid = db.Column(db.Integer, db.ForeignKey('coloridentity.id'))
    lastupdated = db.Column(db.DateTime)

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

@dataclass
class Match(db.Model):
    id: int
    eventid: int
    name: str
    start: datetime
    end: datetime
    winconid: int

    id = db.Column(db.Integer, primary_key=True)
    eventid = db.Column(db.Integer, db.ForeignKey('event.id'))
    name = db.Column(db.String(64))
    start = db.Column(db.DateTime)
    end = db.Column(db.DateTime)
    winconid = db.Column(db.Integer)

@dataclass
class Performance(db.Model):
    id: int
    matchid: int
    deckid: int
    userid: int
    order: int
    placement: int
    username: str
    killedbyname: str

    id = db.Column(db.Integer, primary_key=True)
    username = ''
    matchid = db.Column(db.Integer, db.ForeignKey('match.id'))
    userid = db.Column(db.Integer, db.ForeignKey('user.id'))
    deckid = db.Column(db.Integer, db.ForeignKey('deck.id'))
    order = db.Column(db.Integer)
    placement = db.Column(db.Integer)
    killedby = db.Column(db.Integer, db.ForeignKey('user.id'))
    killedbyname = ''

@dataclass
class MatchDetails:
    match: Match
    performances: list[Performance]

@dataclass
class EventDetails:
    event: Event
    matches: list[MatchDetails]
    decks: list[Deck]

@dataclass
class Decklist(db.Model):
    deckid: int
    cardid: str
    count: int
    iscommander: bool
    iscompanion: bool
    issideboard: bool

    id = db.Column(db.Integer, primary_key=True)
    deckid = db.Column(db.Integer, db.ForeignKey('deck.id'))
    cardid = db.Column(db.String(36), db.ForeignKey('card.id'))
    count = db.Column(db.Integer)
    iscommander = db.Column(db.Boolean)
    iscompanion = db.Column(db.Boolean)
    issideboard = db.Column(db.Boolean)

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
@limiter.limit('')
def create_user(current_user):
    if not current_user.admin:
        return jsonify({'message' : 'Lacking Permissions'})

    data = request.get_json()
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
@limiter.limit('')
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

@app.route('/user', methods=['GET'])
@limiter.limit('')
def get_users():
    users = User.query.all()

    if not users:
         return jsonify({'message' : 'No users found!'})

    return jsonify(users)


###############################################
# Deck
###############################################
@app.route('/deck', methods=['POST'])
@token_required
@limiter.limit('')
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

    new_deck = Deck(userid=current_user.id, name=name, commander=commander, partner=partner, companion=companion, power=power, identityid=cidentity, lastupdated=datetime.datetime.now())
    db.session.add(new_deck)
    db.session.commit()

    return jsonify({'message' : 'New deck created'})

@app.route('/deck', methods=['PUT'])
@token_required
@limiter.limit('')
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
    
    deck.lastupdated = datetime.datetime.now()

    db.session.commit()
    return jsonify({'message' : 'Updated deck'})

@app.route('/deck', methods=['GET'])
@token_required
@limiter.limit('')
def get_user_decks(current_user):
    decks = Deck.query.filter_by(userid=current_user.id).all()
    if not decks:
        return jsonify({'message' : 'No decks found!'}), 204
    
    return jsonify(decks)

@app.route('/userdeckswithcards', methods=['GET'])
@token_required
@limiter.limit('')
def get_specified_user_decks_with_cards(current_user):
    commandercard = aliased(Card)
    partnercard = aliased(Card)
    companioncard = aliased(Card)
    deckandcards = [tuple(row) for row in db.session.query(Deck, commandercard, partnercard, companioncard).select_from(Deck)\
                    .join(commandercard, Deck.commander==commandercard.id, isouter=True)\
                    .join(partnercard, Deck.partner==partnercard.id, isouter=True)\
                    .join(companioncard, Deck.companion==companioncard.id, isouter=True)\
                    .filter(Deck.userid==current_user.id).all()]
    
    if not deckandcards:
        return jsonify({'message' : 'No decks found!'}), 204
    
    performances = Performance.query.filter_by(userid=current_user.id).all()

    return jsonify({"deckandcards": deckandcards, "performances": performances})

@app.route('/userdecks/<userid>', methods=['GET'])
@token_required
@limiter.limit('')
def get_specified_user_decks(current_user, userid):
    decks = Deck.query.filter_by(userid=userid).all()
    if not decks:
        return jsonify({'message' : 'No decks found!'}), 204
    
    return jsonify(decks)

@app.route('/deck/v2', methods=['POST'])
@token_required
@limiter.limit('')
def create_deck_v2(current_user):
    data = request.get_json()
    name = data['name'] if ('name' in data) else 'New Deck'
    list = data['list']
    user = data['user'] if 'user' in data else current_user.publicid

    #commit deck first to use id later
    new_deck = Deck(name=name, userid=User.query.filter_by(publicid=user).first().id, identityid=1, lastupdated=datetime.datetime.now())
    db.session.add(new_deck)
    db.session.commit()

    commander = False
    companion = False
    sideboard = False
    skip = False
    deckcolor = 1
    for lin in list.split('\n'):
        #for each line we need to check if its a card or section identifier then handle appropriately
        skip = False
        cardparseinfo = re.search(DECKLINE_REGEX, lin)
        if not cardparseinfo:
            commander = False
            companion = False
            sideboard = False
            continue
        dbcard = Card.query.filter_by(name=(cardparseinfo.group(2).rstrip().lstrip())).first()
        
        if not dbcard:
            #here we query scryfall for the info
            req = requests.get(url="https://api.scryfall.com/cards/named?exact=" + cardparseinfo.group(2), data=data).content
            time.sleep(0.1) #in order to prevent timeouts we need to throttle to 100ms
            r = json.loads(req)
            print("Fetching " + cardparseinfo.group(2))
            if 'id' not in r or r['set_type'] == "token":
                #means card no exist probably because its a line defining a card type
                if "commander" in lin.lower():
                    commander = True
                    companion = False
                    sideboard = False
                elif "companion" in lin.lower():
                    commander = False
                    companion = True
                    sideboard = True
                elif "sideboard" in lin.lower():
                    commander = False
                    companion = False
                    sideboard = True
                else:
                    commander = False
                    companion = False
                    sideboard = False
                skip = True
                continue
            dbcard = Card.query.filter_by(id=r['id']).first() #sanity check because sometimes it trys to add things that exist
            if not dbcard:
                dbcard = Card(id=r['id'], name=r['name'], mv=r['cmc'], cost=(r['mana_cost'] if 'mana_cost' in r else r['card_faces'][0]['mana_cost']), identityid=scryfall_color_converter(r['color_identity'])) 
            db.session.add(dbcard)
            db.session.commit()
        else:
            print("FOUND " + dbcard.name)
        
        if dbcard and not skip:
            #add the card entry to deck if relevant (commander etc) and decklist entry
            if commander or (cardparseinfo.group(3) and cardparseinfo.group(3).find('CMDR')):
                if not new_deck.commander:
                    new_deck.commander = dbcard.id
                    new_deck.identityid = dbcard.identityid
                else:
                    new_deck.partner = dbcard.id
                    color1 = Coloridentity.query.filter_by(id=new_deck.identityid).first()
                    color2 = Coloridentity.query.filter_by(id=dbcard.identityid).first()
                    final_color = Coloridentity.query.filter_by(
                        green=(color1.green or color2.green),
                        red=(color1.red or color2.red),
                        blue=(color1.blue or color2.blue),
                        black=(color1.black or color2.black),
                        white=(color1.white or color2.white),
                        ).first()
                    new_deck.identityid = final_color.id
            elif companion:
                new_deck.companion = dbcard.id
            print("Adding " + dbcard.name)
            cardcount = cardparseinfo.group(1)
            cardcount = re.sub("[^0-9]", "", cardcount)
            if not cardcount:
                cardcount = 1
            new_listentry = Decklist(deckid=new_deck.id, cardid=dbcard.id, iscommander=commander, count=cardcount, iscompanion=companion, issideboard=sideboard)
            db.session.add(new_listentry)
            db.session.commit()

    return jsonify({'message' : 'New deck created', 'deckid': new_deck.id})

@app.route('/deck/v2/<id>', methods=['GET'])
@token_required
@limiter.limit('')
def get_deck_v2(current_user, id):
    deck = Deck.query.filter_by(id=id).first()
    cardlist = [tuple(row) for row in db.session.query(Decklist, Card).join(Card).filter(Decklist.deckid == id).all()]
    if not deck:
        return jsonify({'message' : 'No decks found!'}), 204
    
    return jsonify({"deck": deck, "cardlist":cardlist})

@app.route('/deck/v2/<id>', methods=['PUT'])
@token_required
@limiter.limit('')
def update_deck_v2(current_user, id):
    data = request.get_json()
    deck = Deck.query.filter_by(id=id).first()
    if not deck:
        return jsonify({'message' : 'No decks found!'}), 204
    
    if not 'prop' in data or not 'val' in data:
        return jsonify({'message' : 'Incomplete data provided!'}), 204
    
    if data['prop'] == 'commander':
        if(deck.commander):
            oldcommander = Decklist.query.filter_by(deckid=id).filter_by(cardid=deck.commander).first()
            oldcommander.iscommander = False
        if not data['val']:
            deck.commander = None
        else:
            deck.commander = data['val']
            cardentry = Decklist.query.filter_by(deckid=id).filter_by(cardid=data['val']).first()
            cardentry.iscommander = True
            if not deck.partner:
                cardinfo = Card.query.filter_by(id=cardentry.cardid).first()
                deck.identityid = cardinfo.identityid
            else:
                cardinfo = db.session.query(Card, Coloridentity).join(Coloridentity).filter(Card.id == cardentry.cardid).all()
                cardinfo2 = db.session.query(Card, Coloridentity).join(Coloridentity).filter(Card.id == deck.partner).all()
                final_color = Coloridentity.query.filter_by(
                        green=(cardinfo[0].Coloridentity.green or cardinfo2[0].Coloridentity.green),
                        red=(cardinfo[0].Coloridentity.red or cardinfo2[0].Coloridentity.red),
                        blue=(cardinfo[0].Coloridentity.blue or cardinfo2[0].Coloridentity.blue),
                        black=(cardinfo[0].Coloridentity.black or cardinfo2[0].Coloridentity.black),
                        white=(cardinfo[0].Coloridentity.white or cardinfo2[0].Coloridentity.white),
                        ).first()
                deck.identityid = final_color.id
    if data['prop'] == 'partner':
        if(deck.partner):
            oldpartner = Decklist.query.filter_by(deckid=id).filter_by(cardid=deck.partner).first()
            oldpartner.ispartner = False
        if not data['val']:
            deck.partner = None
            if deck.commander:
                deckcommander = Card.query.filter_by(id=deck.commander).first()
                deck.identityid = deckcommander.identityid
        else:
            deck.partner = data['val']
            cardentry = Decklist.query.filter_by(deckid=id).filter_by(cardid=data['val']).first()
            cardentry.ispartner = True
            if not deck.commander:
                cardinfo = Card.query.filter_by(id=cardentry.cardid).first()
                deck.identityid = cardinfo.identityid
            else:
                cardinfo = db.session.query(Card, Coloridentity).join(Coloridentity).filter(Card.id == cardentry.cardid).all()
                cardinfo2 = db.session.query(Card, Coloridentity).join(Coloridentity).filter(Card.id == deck.commander).all()
                final_color = Coloridentity.query.filter_by(
                        green=(cardinfo[0].Coloridentity.green or cardinfo2[0].Coloridentity.green),
                        red=(cardinfo[0].Coloridentity.red or cardinfo2[0].Coloridentity.red),
                        blue=(cardinfo[0].Coloridentity.blue or cardinfo2[0].Coloridentity.blue),
                        black=(cardinfo[0].Coloridentity.black or cardinfo2[0].Coloridentity.black),
                        white=(cardinfo[0].Coloridentity.white or cardinfo2[0].Coloridentity.white),
                        ).first()
                deck.identityid = final_color.id
    if data['prop'] == 'companion':
        if(deck.companion):
            oldcompanion = Decklist.query.filter_by(deckid=id).filter_by(cardid=deck.companion).first()
            oldcompanion.iscompanion = False
            oldcompanion.issideboard = False
        if not data['val']:
            deck.companion = None
        else:
            deck.companion = data['val']
            cardentry = Decklist.query.filter_by(deckid=id).filter_by(cardid=data['val']).first()
            cardentry.iscompanion = True
            cardentry.issideboard = True
    if data['prop'] == 'name':
        deck.name = data['val']
    if data['prop'] == 'sideboard' and data['val']:
        cardentry = Decklist.query.filter_by(deckid=id).filter_by(cardid=data['val']).first()
        cardentry.issideboard = True
    if data['prop'] == '-sideboard' and data['val']:
        cardentry = Decklist.query.filter_by(deckid=id).filter_by(cardid=data['val']).first()
        cardentry.issideboard = False
    
    db.session.commit()
    return jsonify({'message' : 'Deck updated'})

@app.route('/removedeck/<id>', methods=['PUT'])
@token_required
@limiter.limit('')
def remove_deck(current_user, id):
    performances = Performance.query.filter_by(deckid = id).first()
    if performances:
        return jsonify({'message' : 'Deck cannot be deleted. It is used in matches'}), 204
    print("stage 2")
    decklist = Decklist.query.filter_by(deckid = id).all()
    for dlentry in decklist:
        db.session.delete(dlentry)
    print("stage 3")
    deck = Deck.query.filter_by(id = id).first()
    print(deck)
    db.session.delete(deck)
    db.session.commit()

    return jsonify({'message' : 'Deck deleted'})

###############################################
# Events
###############################################
@app.route('/event', methods=['POST'])
@token_required
@limiter.limit('')
def create_event(current_user):
    data = request.get_json()
    current_time = datetime.datetime.utcnow()
    last_day = current_time - datetime.timedelta(days=1)

    eventstoday = Event.query.filter(Event.time > last_day).count()
    if eventstoday > 0:
        return jsonify({'message' : 'Event already created for today'})
    
    weekly_count = Event.query.filter_by(themed=False).count()
    name = 'Weekly ' + str(weekly_count + 1)
    time = datetime.datetime.now()
    themed = False

    new_event = Event(name=name, time=time, themed=themed)
    db.session.add(new_event)
    db.session.commit()

    return jsonify({'message' : 'New event created'})

@app.route('/event', methods=['PUT'])
@token_required
@limiter.limit('')
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
@limiter.limit('')
def get_events(current_user):
    events = Event.query.all()
    if not events:
        return jsonify({'message' : 'No events found!'}), 204
    
    return jsonify(events)

@app.route('/event/<id>', methods=['GET'])
@token_required
@limiter.limit('')
def get_event_details(current_user, id):
    event = Event.query.filter_by(id=id).first()
    if not event:
        return jsonify({'message' : 'No event found!'}), 204
    
    matches = Match.query.filter_by(eventid=id).all()

    def matchperformance(m):
        performances = Performance.query.filter_by(matchid=m.id).all()
        for p in performances:
            p.username = User.query.filter_by(id=p.userid).first().username
            killedbyuser = User.query.filter_by(id=p.killedby).first()
            if killedbyuser:
                p.killedbyname = killedbyuser.username
        return MatchDetails(match=m, performances=performances)
    
    matchdetails = list(map(matchperformance, matches))
    
    #adding decks to the event details since we will need it however this should change in the future to being grabbed as a per user query as needed
    decks = Deck.query.all()

    if not matches:
        matches = []
    
    if not decks:
        decks = []
    
    eventDetails = EventDetails(event=event, matches=matchdetails, decks=decks)
    
    return jsonify(eventDetails)


###############################################
# Matches
###############################################
@app.route('/match', methods=['POST'])
@token_required
@limiter.limit('')
def create_match(current_user):
    data = request.get_json()

    count = Match.query.filter_by(eventid=data).count()
    name = 'Match ' + str(count + 1)

    new_match = Match(name=name, eventid=data)
    db.session.add(new_match)
    db.session.commit()

    return jsonify({'message' : 'New match created'})

@app.route('/match', methods=['PUT'])
@token_required
@limiter.limit('')
def update_match(current_user):
    data = request.get_json()
    rawmatch = data['match']
    match = Match.query.filter_by(id=rawmatch['id']).first()
    if not match:
        return jsonify({'message' : 'No match found!'})
    
    if 'prop' in data:
        if data['prop'] == 'start':
            match.start = rawmatch['start']
        if data['prop'] == 'end':
            match.end = rawmatch['end']
        if data['prop'] == 'delete':
            if not match.start: #can only delete if we havent started the match for safety reasons
                performances = Performance.query.filter_by(matchid=rawmatch['id']).all()
                if performances:
                    db.session.delete(performances)
                db.session.delete(match)

    db.session.commit()
    return jsonify({'message' : 'Updated match'})


###############################################
# Performance
###############################################
@app.route('/performance', methods=['POST'])
@token_required
@limiter.limit('')
def create_performance(current_user):
    data = request.get_json()
    userinfo = data['user']
    matchinfo = data['match']
    userid = User.query.filter_by(publicid=userinfo['publicid']).first().id

    new_performance = Performance(userid=userid, matchid=matchinfo['id'])
    db.session.add(new_performance)
    db.session.commit()

    return jsonify({'message' : 'New deck created'})

@app.route('/performance', methods=['PUT'])
@token_required
@limiter.limit('')
def update_performance(current_user):
    data = request.get_json()
    
    performance = Performance.query.filter_by(id=data['id']).first()
    if not performance:
        return jsonify({'message' : 'No performance found!'})
    
    if 'placement' in data:
        performance.placement = data['placement']
    
    if 'order' in data:
        performance.order = data['order']

    if 'deckid' in data:
        performance.deckid = data['deckid']
    
    if 'killedby' in data:
        user = User.query.filter_by(publicid=data['killedby']).first()
        if user:
            performance.killedby = user.id
    
    if 'delete' in data:
        match = Match.query.filter_by(id=performance.matchid).first()
        if not match.start:
            db.session.delete(performance)

    db.session.commit()
    return jsonify({'message' : 'Updated performance'})

@app.route('/performance/<id>', methods=['GET'])
@token_required
@limiter.limit('')
def get_match_performances(current_user, id):
    data = request.get_json()
    performances = Performance.query.filter_by(matchid=id).all()
    if not performances:
        return jsonify({'message' : 'No performances found!'}), 204
    
    return jsonify(performances)


###############################################
# Login
###############################################
@app.route('/login', methods=['POST'])
@limiter.limit("10/hour", override_defaults=False)
def login():
    data = request.get_json()
    if not data or not data['username'] or not data['password']:
        return make_response('Could not verify', 401, {'WWW-authenticate' : 'Basic realm="Login Required"'})
    
    user = User.query.filter_by(username=data['username']).first()
    if not user:
        return jsonify('Could not verify', 401, {'WWW-authenticate' : 'Basic realm="Login Required"'})

    if check_password_hash(user.hash, data['password']):
        token = jwt.encode({'username': user.username, 'publicid':user.publicid, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)}, app.config['SECRET_KEY'])
        return jsonify({'token': token, 'username': user.username, 'publicid': user.publicid}) #TODO: Define a model for the response data

    return jsonify('Could not verify' + user.hash + data['password'], 401, {'WWW-authenticate' : 'Basic realm="Login Required"'})


###############################################
# Util
###############################################
@app.route('/colors', methods=['GET'])
@limiter.limit('')
def get_coloridentities():
    colors = Coloridentity.query.all()
    return jsonify(colors)

def scryfall_color_converter(colors):
    #this is about to get ugly but itl save time later :["B","G","R","U","W"]
    colorbase = ['0','0','0','0','0']
    for c in colors:
        if c == "B":
            colorbase[0] = '1'
        if c == "G":
            colorbase[1] = '1'
        if c == "R":
            colorbase[2] = '1'
        if c == "U":
            colorbase[3] = '1'
        if c == "W":
            colorbase[4] = '1'
    return colorbase_to_id("".join(colorbase))

def colorbase_to_id(cb):
    #becomes obsolete if ids change but just faster for rn
    if(cb == '00000'): return 1
    if(cb == '00010'): return 2
    if(cb == '00001'): return 3
    if(cb == '01000'): return 4
    if(cb == '00100'): return 5
    if(cb == '10000'): return 6

    if(cb == '00011'): return 7
    if(cb == '01001'): return 8
    if(cb == '01100'): return 9
    if(cb == '10100'): return 10
    if(cb == '10010'): return 11
    if(cb == '00101'): return 12
    if(cb == '11000'): return 13
    if(cb == '00110'): return 14
    if(cb == '10001'): return 15
    if(cb == '01010'): return 16
    
    if(cb == '01011'): return 17
    if(cb == '11001'): return 18
    if(cb == '10011'): return 19
    if(cb == '10110'): return 20
    if(cb == '00111'): return 21
    if(cb == '11100'): return 22
    if(cb == '10101'): return 23
    if(cb == '01101'): return 24
    if(cb == '11010'): return 25
    if(cb == '01110'): return 26

    if(cb == '11110'): return 27
    if(cb == '11101'): return 28
    if(cb == '01111'): return 29
    if(cb == '11011'): return 30
    if(cb == '10111'): return 31
    if(cb == '11111'): return 32

if __name__ == "__main__":
    app.run(debug=True)

from flask_sqlalchemy import SQLAlchemy
from dataclasses import dataclass
import datetime

db = SQLAlchemy()

@dataclass
class User(db.Model):
    id: int
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
    id: str
    name: str
    typeline: str
    oracletext: str
    mv: int
    cost: str
    identityid: int
    banned: bool
    watchlist: bool
    custom: bool
    transform: bool

    id = db.Column(db.String(46), primary_key=True)
    name = db.Column(db.String(64))
    typeline = db.Column(db.String(128))
    oracletext = db.Column(db.String(2000))
    mv = db.Column(db.Integer)
    cost = db.Column(db.String(64))
    identityid = db.Column(db.Integer, db.ForeignKey('coloridentity.id'))
    banned = db.Column(db.Boolean)
    watchlist = db.Column(db.Boolean)
    custom = db.Column(db.Boolean)
    transform = db.Column(db.Boolean)

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
    islegal: bool
    picpos: str
    image: str

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
    islegal = db.Column(db.Boolean)
    picpos = db.Column(db.String(24))
    image = db.Column(db.String(256))

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
    weekly: bool

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    time = db.Column(db.DateTime)
    themed = db.Column(db.Boolean)
    themeid = db.Column(db.Integer, db.ForeignKey('theme.id'))
    weekly = db.Column(db.Boolean)

@dataclass
class Match(db.Model):
    id: int
    eventid: int
    name: str
    start: datetime
    end: datetime
    winconid: int
    power: int

    id = db.Column(db.Integer, primary_key=True)
    eventid = db.Column(db.Integer, db.ForeignKey('event.id'))
    name = db.Column(db.String(64))
    start = db.Column(db.DateTime)
    end = db.Column(db.DateTime)
    winconid = db.Column(db.Integer)
    power = db.Column(db.Integer)

@dataclass
class Performance(db.Model):
    id: int
    matchid: int
    deckid: int
    userid: int
    order: int
    placement: int
    username: str
    killedby: int
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
class Theme(db.Model):
    id: int
    name: str
    stylename: str

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))
    stylename = db.Column(db.String(45))

@dataclass
class MatchDetails:
    match: Match
    performances: list[Performance]

@dataclass
class EventDetails:
    event: Event
    matches: list[MatchDetails]
    decks: list[Deck]
    theme: Theme

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

@dataclass
class Printing(db.Model):
    id: str
    cardid: str
    cardimage: str
    artcrop: str
    releasedate: datetime

    id = db.Column(db.String(36), primary_key=True)
    cardid = db.Column(db.String(46), db.ForeignKey('card.id'))
    cardimage = db.Column(db.String(256))
    artcrop = db.Column(db.String(256))
    releasedate = db.Column(db.DateTime)

@dataclass
class Cardtoken(db.Model):
    id: str
    cardid: str
    tokenid: str

    id = db.Column(db.Integer, primary_key=True)
    cardid = db.Column(db.String(46), db.ForeignKey('card.id'))
    tokenid = db.Column(db.String(46))
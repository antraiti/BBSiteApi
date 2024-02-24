from flask import request, jsonify
import datetime
from sqlalchemy.orm import aliased
from models import User, Deck, Performance, Event, EventDetails, Match, MatchDetails, Theme, Card
from main import app, limiter, token_required, db

@app.route('/event', methods=['POST'])
@token_required
@limiter.limit('')
def create_event(current_user):
    data = request.get_json()
    current_time = datetime.datetime.utcnow()
    last_day = current_time - datetime.timedelta(days=1)
    name = ""
    themed = False
    weekly = True

    eventstoday = Event.query.filter(Event.time > last_day).count()
    if eventstoday > 0:
        return jsonify({'message' : 'Event already created for today'})
    
    if 'themed' in data:
        themed = data['themed']
    if 'themeid' in data:
        themeid = data['themeid']
    if 'weekly' in data:
        weekly = data['weekly']
    
    if weekly:
        weekly_count = Event.query.filter_by(weekly=True).count()
        name = 'Weekly ' + str(weekly_count + 92)
    
    if 'name' in data:
        if weekly and themed:
            name = name + ": "
        name = name + data['name']

    new_event = Event(name=name, time=current_time, themed=themed, weekly=weekly)

    if 'themeid' in data and int(themeid) > 0: #probably a better way to do this
        new_event.themeid = themeid

    db.session.add(new_event)
    db.session.commit()

    return jsonify({'message' : 'New event created'})

@app.route('/event', methods=['PUT'])
@token_required
@limiter.limit('')
def update_event(current_user):
    data = request.get_json()
    print(data)
    
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
    theme = Theme.query.filter_by(id=event.themeid).first()

    def matchperformance(m):
        performances = Performance.query.filter_by(matchid=m.id).all()
        for p in performances:
            p.username = User.query.filter_by(id=p.userid).first().username
            killedbyuser = User.query.filter_by(id=p.killedby).first()
            if killedbyuser:
                p.killedbyname = killedbyuser.username
        return MatchDetails(match=m, performances=performances)
    
    matchdetails = list(map(matchperformance, matches))
    
    commandercard = aliased(Card)
    partnercard = aliased(Card)
    companioncard = aliased(Card)
    decks = [tuple(row) for row in db.session.query(Deck, commandercard, partnercard, companioncard).select_from(Deck)\
                    .join(commandercard, Deck.commander==commandercard.id, isouter=True)\
                    .join(partnercard, Deck.partner==partnercard.id, isouter=True)\
                    .join(companioncard, Deck.companion==companioncard.id, isouter=True)\
                    .all()]

    if not matches:
        matches = []
    
    if not decks:
        decks = []
    
    eventDetails = EventDetails(event=event, matches=matchdetails, decks=decks, theme=theme)
    
    return jsonify(eventDetails)

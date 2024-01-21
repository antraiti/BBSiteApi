from flask import request, jsonify
import datetime
from models import User, Deck, Performance, Event, EventDetails, Match, MatchDetails
from main import app, limiter, token_required, db

@app.route('/event', methods=['POST'])
@token_required
@limiter.limit('')
def create_event(current_user):
    data = request.get_json()
    current_time = datetime.datetime.utcnow()
    last_day = current_time - datetime.timedelta(days=1)
    name = "New Event"
    themed = False
    weekly = True

    eventstoday = Event.query.filter(Event.time > last_day).count()
    if eventstoday > 0:
        return jsonify({'message' : 'Event already created for today'})
    
    if 'name' in data:
        name = data['name']
    if 'themed' in data:
        themed = data['themed']
    if 'weekly' in data:
        weekly = data['weekly']
    
    if weekly and not themed:
        weekly_count = Event.query.filter_by(weekly=True).count()
        name = 'Weekly ' + str(weekly_count + 1)

    new_event = Event(name=name, time=current_time, themed=themed, weekly=weekly)
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

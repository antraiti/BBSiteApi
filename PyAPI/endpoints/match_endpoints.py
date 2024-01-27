import datetime, random
from flask import request, jsonify
from models import Performance, Match
from main import app, limiter, token_required, db

@app.route('/match', methods=['POST'])
@token_required
@limiter.limit('')
def create_match(current_user):
    data = request.get_json()
    print("new match " + data)
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

    if 'matchid' in data:
        matchid = data['matchid']
    else:
        matchid = data['match']['id'] #old method

    match = Match.query.filter_by(id=matchid).first()
    if not match:
        return jsonify({'message' : 'No match found!'})
    
    if 'prop' in data:
        if data['prop'] == 'start':
            match.start = datetime.datetime.utcnow()
            #pick a random person to go first
            performances = Performance.query.filter_by(matchid=matchid).all()
            if performances:
                performances[random.randint(0, len(performances)-1)].order = 1
        if data['prop'] == 'end':
            match.end = datetime.datetime.utcnow()
        if data['prop'] == 'delete':
            if not match.start: #can only delete if we havent started the match for safety reasons
                performances = Performance.query.filter_by(matchid=matchid).all()
                if performances:
                    for p in performances:
                        db.session.delete(p)
                        db.session.commit()
                db.session.delete(match)

    db.session.commit()
    return jsonify({'message' : 'Updated match'})
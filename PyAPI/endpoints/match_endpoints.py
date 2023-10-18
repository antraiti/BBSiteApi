from flask import request, jsonify
from models import Performance, Match
from main import app, limiter, token_required, db

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
                    for p in performances:
                        db.session.delete(p)
                        db.session.commit()
                db.session.delete(match)

    db.session.commit()
    return jsonify({'message' : 'Updated match'})
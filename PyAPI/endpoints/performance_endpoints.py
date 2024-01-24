from flask import request, jsonify
from flask_sqlalchemy import SQLAlchemy
from models import User, Performance, Match
from main import app, limiter, token_required, db

@app.route('/performance', methods=['POST'])
@token_required
@limiter.limit('')
def create_performance(current_user):
    data = request.get_json()
    print(data)
    
    if 'matchid' in data: #new way
        matchID = data['matchid']
    else:
        matchID = data['match']['id']
    
    if 'user' in data: #old way using whole user
        userinfo = data['user']
        userid = User.query.filter_by(publicid=userinfo['publicid']).first().id
    else:
        userid = User.query.filter_by(publicid=data['userid']).first().id

    new_performance = Performance(userid=userid, matchid=matchID)
    db.session.add(new_performance)
    db.session.commit()

    return jsonify({'message' : 'New deck created'})

@app.route('/performance', methods=['PUT'])
@token_required
@limiter.limit('')
def update_performance(current_user):
    data = request.get_json()
    print(request.get_json())
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
    if 'killedbyuid' in data:
        if data['killedbyuid'] == 'Killed By':
            performance.killedby = None
        else:
            user = User.query.filter_by(id=data['killedbyuid']).first()
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

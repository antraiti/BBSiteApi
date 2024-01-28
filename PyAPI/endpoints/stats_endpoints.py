from flask import request, jsonify
from sqlalchemy.orm import aliased
import requests, time, json
import re
import datetime
from helpers import scryfall_color_converter
from models import User, Card, Deck, Decklist, Performance, Coloridentity
from main import app, limiter, token_required, db

@app.route('/stats/user/<id>/simple', methods=['GET'])
@token_required
@limiter.limit('')
def get_user_stats(current_user, id):
    user = User.query.filter_by(id=id).first()
    if not user:
        return jsonify({'message' : 'No user found!'}), 204
    
    performances = Performance.query.filter_by(userid=user.id).all()

    matches_played = 0
    matches_won = 0
    average_placement = 0

    for p in performances:
        if p.placement == None:
            continue
        if p.placement == 1:
            matches_won += 1
        matches_played += 1
        average_placement += p.placement
    if matches_played > 0:
        average_placement = average_placement/matches_played
    
    return jsonify({"matchesplayed": matches_played, "matcheswon": matches_won, "averageplacement": average_placement})
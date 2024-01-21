from flask import request, jsonify
from sqlalchemy.orm import aliased
import requests, time, json
import re
import datetime
from helpers import scryfall_color_converter
from models import User, Card, Deck, Decklist, Performance, Coloridentity
from main import app, limiter, token_required, db

@app.route('/stats/user/<id>', methods=['GET'])
@token_required
@limiter.limit('')
def get_user_stats(current_user, id):
    user = User.query.filter_by(publicid=id).first()
    if not user:
        return jsonify({'message' : 'No user found!'}), 204
    
    performances = Performance.query.filter_by(userid=user.id).all()

    matches_played = performances.count()
    #matches_won = 

        
    return jsonify({"matches_played": matches_played})
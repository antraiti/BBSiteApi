from flask import request, jsonify
from sqlalchemy.orm import aliased
import requests, time, json
import re
import datetime
from helpers import scryfall_color_converter
from models import User, Card, Deck, Decklist, Performance, Coloridentity
from main import app, limiter, token_required, db

@app.route('/card/<id>', methods=['GET'])
@token_required
@limiter.limit('')
def get_card(current_user, id):
    card = Card.query.filter_by(id=id).first()
    if not card:
        return jsonify({'message' : 'No cards found!'}), 204
        
    return jsonify(card)
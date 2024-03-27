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

@app.route('/banlist', methods=['GET'])
@limiter.limit('')
def get_banlist():
    banlist = Card.query.filter_by(banned=1).all()
    if not banlist:
        return jsonify({'message' : 'No banlist found!'}), 204
        
    return jsonify(banlist)

@app.route('/watchlist', methods=['GET'])
@limiter.limit('')
def get_watchlist():
    watchlist = Card.query.filter_by(watchlist=1).all()
    if not watchlist:
        return jsonify({'message' : 'No watchlist found!'}), 204
        
    return jsonify(watchlist)
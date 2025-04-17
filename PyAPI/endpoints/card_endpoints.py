import re
from flask import request, jsonify
from sqlalchemy.orm import aliased
from helpers import scryfall_color_converter
from models import Card
from main import app, limiter, token_required, db

DECKLINE_REGEX = r'^(\d+x?) *([^\(\n\*]+) *(?:\(.*\))? *(?:[\d]+|\w\w\w-\d+)? *(\*CMDR\*)?'

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

@app.route('/fromdecklist', methods=['POST'])
@token_required
@limiter.limit('')
def cards_from_decklist(current_user):
    list = request.get_json() # data passed in is just decklist
    cards = []

    #iterate list
    for lin in list.split('\n'):
        #for each line we need to check if its a card or section identifier then handle appropriately
        cardparseinfo = re.search(DECKLINE_REGEX, lin)
        # group 1: count
        # group 2: cardname
        # group 3: commander flag
        
        if not cardparseinfo:
            output += ("COULD NOT PARSE LINE: " + lin)
            continue
        #try to get from db first
        dbcard = Card.query.filter_by(name=(cardparseinfo.group(2).rstrip().lstrip())).first()
        print(dbcard)
        
        # if we dont find the cardname in our db we fetch from scryfall
        # NOTE: this will also happen sometimes when we have the cardname but it doesnt properly match
        if dbcard:
            print(dbcard)
            cards.append(dbcard)
        

    return jsonify(cards)
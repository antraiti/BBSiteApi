import json
import re
import time
from flask import request, jsonify
import requests
from sqlalchemy.orm import aliased
from helpers import scryfall_color_converter
from models import Card, Cardtoken, Printing
from main import app, limiter, token_required, db

OLD_DECKLINE_REGEX = r'^(\d+x?) *([^\(\n\*]+) *(?:\(.*\))? *(?:[\d]+|\w\w\w-\d+)? *(\*CMDR\*)?'
DECKLINE_REGEX = r'^(\d+x?)? *([^\(\n\*]+) *(?:\(.*\))? *(?:[\d]+|\w\w\w-\d+)? *(\*CMDR\*)?'

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

    SELECTED_REGEX = DECKLINE_REGEX if list.split('\n')[0] != "oldregex" else OLD_DECKLINE_REGEX

    #iterate list
    for lin in list.split('\n'):
        #for each line we need to check if its a card or section identifier then handle appropriately
        cardparseinfo = re.search(SELECTED_REGEX, lin)
        # group 1: count
        # group 2: cardname
        # group 3: commander flag
        
        if not cardparseinfo:
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

# TODO: Adding token information to db
# 1. Update DB schema and api models appropriately
#      - tokens can probably just be added to the normal printing table as well since they use proper oracle ids

# 2. Make POST function for processing all cards and adding tokens and their printings if missing
@app.route('/bulktokens', methods=['POST'])
@token_required
@limiter.limit('')
def add_all_tokens(current_user):
    seenTokens = set()
    realCards = Card.query.filter_by(custom = None).all()
    print(f"{len(realCards)} cards found")
    counter = 0
    for card in realCards:
        counter += 1
        print(f"{counter} / {len(realCards)} - {card.name} {card.id}")
        if card.id.endswith("/back"):
            continue
        cardinfo = requests.get(url="https://api.scryfall.com/cards/search?q=oracleid=" + card.id).content
        time.sleep(0.1) #in order to prevent timeouts we need to throttle to 100ms
        rp = json.loads(cardinfo)
        if rp:
            if 'all_parts' not in rp['data'][0]:
                continue
            print(f'Found parts {card.name} {card.id}')
            for c in rp["data"][0]["all_parts"]:
                if c["component"] == "token" or c['type_line'].startswith('Emblem'):
                    print(f'Found token {c["name"]} {card.name} {card.id}')
                    tokenInfo = requests.get(url=c["uri"]).content
                    time.sleep(0.1) #in order to prevent timeouts we need to throttle to 100ms
                    ti = json.loads(tokenInfo)
                    if "oracle_id" in ti:
                        print(f'Getting token for {card.name} {card.id}')
                        dbtoken = Cardtoken(cardid=card.id, tokenid=ti["oracle_id"]) 
                        db.session.add(dbtoken)
                        if ti["oracle_id"] in seenTokens:
                            print(f'Already retrieved printings for {ti["name"]} {ti["oracle_id"]}')
                            continue
                        seenTokens.add(ti["oracle_id"])
                        tokenPrintings = requests.get(url="https://api.scryfall.com/cards/search?q=oracleid=" + ti["oracle_id"] + "&unique=prints").content
                        time.sleep(0.1) #in order to prevent timeouts we need to throttle to 100ms
                        tp = json.loads(tokenPrintings)
                        if tp:
                            for p in tp["data"]:
                                existingPrint = Printing.query.filter_by(id=p["id"]).first()
                                if not existingPrint:
                                    print(f'Getting adding print for {ti["name"]} {ti["oracle_id"]}')
                                    if "image_uris" in p:
                                        print("once face " + p["id"])
                                        new_printing = Printing(id=p["id"], cardid=ti["oracle_id"], cardimage=p["image_uris"]["large"], artcrop=p["image_uris"]["art_crop"])
                                        db.session.add(new_printing)
                                    else:
                                        print("two face")
                                        new_printing_front = Printing(id=p["id"], cardid=ti["oracle_id"], cardimage=p["card_faces"][0]["image_uris"]["large"], artcrop=p["card_faces"][0]["image_uris"]["art_crop"])
                                        db.session.add(new_printing_front)
                                        new_printing_back = Printing(id=(p["id"]+"/back"), cardid=(ti["oracle_id"]+"/back"), cardimage=p["card_faces"][1]["image_uris"]["large"], artcrop=p["card_faces"][1]["image_uris"]["art_crop"])
                                        db.session.add(new_printing_back)
    db.session.commit()

    return jsonify()


# TODO: Adding art fetching
# 1. Add POST function to update given a SINGLE card fetch its printings and add any that are missing
# 2. Add POST function to iterate ALL cards and update printings that are missing. 
#     - (this should pull the latest bulk data to save time)


from flask import request, jsonify
from sqlalchemy.orm import aliased
import requests, time, json
import re
import datetime
from helpers import scryfall_color_converter
from models import User, Card, Deck, Decklist, Performance, Coloridentity
from main import app, limiter, token_required, db

DECKLINE_REGEX = r'^(\d+x?)?\s*([^(\n\*]+)\s*(?:\(.*\))?\s*(\*CMDR\*)?'

@app.route('/deck', methods=['POST'])
@token_required
@limiter.limit('')
def create_deck(current_user):
    data = request.get_json()
    name = 'New Deck'
    link = ''
    commander = ''
    partner = ''
    companion = ''
    power = 0
    cidentity = 1

    if 'name' in data:
        name = data['name']
    if 'link' in data:
        name = data['link']
    if 'commander' in data:
        name = data['commander']
    if 'partner' in data:
        name = data['partner']
    if 'companion' in data:
        name = data['companion']
    if 'power' in data:
        name = data['power']
    if 'cidentity' in data:
        name = data['cidentity']

    new_deck = Deck(userid=current_user.id, name=name, commander=commander, partner=partner, companion=companion, power=power, identityid=cidentity, lastupdated=datetime.datetime.now())
    db.session.add(new_deck)
    db.session.commit()

    return jsonify({'message' : 'New deck created'})

@app.route('/deck', methods=['PUT'])
@token_required
@limiter.limit('')
def update_deck(current_user):
    data = request.get_json()

    deck = Deck.query.filter_by(id=data['id']).first()
    if not deck:
        return jsonify({'message' : 'No deck found!'})
    
    if 'name' in data:
        deck.name = data['name']
    if 'link' in data:
        deck.link = data['link']
    if 'commander' in data:
        deck.commander = data['commander']
    if 'partner' in data:
        deck.partner = data['partner']
    if 'companion' in data:
        deck.companion = data['companion']
    if 'power' in data:
        deck.power = data['power']
    if 'identityid' in data:
        deck.identityid = data['identityid']
    
    deck.lastupdated = datetime.datetime.now()

    db.session.commit()
    return jsonify({'message' : 'Updated deck'})

@app.route('/deck', methods=['GET'])
@token_required
@limiter.limit('')
def get_user_decks(current_user):
    decks = Deck.query.filter_by(userid=current_user.id).all()
    if not decks:
        return jsonify({'message' : 'No decks found!'}), 204
    
    return jsonify(decks)

@app.route('/userdeckswithcards', methods=['GET'])
@token_required
@limiter.limit('')
def get_specified_user_decks_with_cards(current_user):
    commandercard = aliased(Card)
    partnercard = aliased(Card)
    companioncard = aliased(Card)
    deckandcards = [tuple(row) for row in db.session.query(Deck, commandercard, partnercard, companioncard).select_from(Deck)\
                    .join(commandercard, Deck.commander==commandercard.id, isouter=True)\
                    .join(partnercard, Deck.partner==partnercard.id, isouter=True)\
                    .join(companioncard, Deck.companion==companioncard.id, isouter=True)\
                    .filter(Deck.userid==current_user.id).all()]
    
    if not deckandcards:
        return jsonify({'message' : 'No decks found!'}), 204
    
    performances = Performance.query.filter_by(userid=current_user.id).all()

    return jsonify({"deckandcards": deckandcards, "performances": performances})

@app.route('/userdecks/<userid>', methods=['GET'])
@token_required
@limiter.limit('')
def get_specified_user_decks(current_user, userid):
    decks = Deck.query.filter_by(userid=userid).all()
    if not decks:
        return jsonify({'message' : 'No decks found!'}), 204
    
    return jsonify(decks)

@app.route('/deck/v2', methods=['POST'])
@token_required
@limiter.limit('')
def create_deck_v2(current_user):
    data = request.get_json()
    name = data['name'] if ('name' in data) else 'New Deck'
    list = data['list']
    user = data['user'] if 'user' in data else current_user.publicid

    #commit deck first to use id later
    new_deck = Deck(name=name, userid=User.query.filter_by(publicid=user).first().id, identityid=1, lastupdated=datetime.datetime.now())
    db.session.add(new_deck)
    db.session.commit()

    commander = False
    companion = False
    sideboard = False
    skip = False
    deckcolor = 1
    for lin in list.split('\n'):
        #for each line we need to check if its a card or section identifier then handle appropriately
        skip = False
        cardparseinfo = re.search(DECKLINE_REGEX, lin)
        if not cardparseinfo:
            commander = False
            companion = False
            sideboard = False
            continue
        dbcard = Card.query.filter_by(name=(cardparseinfo.group(2).rstrip().lstrip())).first()
        
        if not dbcard:
            #here we query scryfall for the info
            req = requests.get(url="https://api.scryfall.com/cards/named?exact=" + cardparseinfo.group(2), data=data).content
            time.sleep(0.1) #in order to prevent timeouts we need to throttle to 100ms
            r = json.loads(req)
            print("Fetching " + cardparseinfo.group(2))
            if 'id' not in r or r['set_type'] == "token":
                #means card no exist probably because its a line defining a card type
                if "commander" in lin.lower():
                    commander = True
                    companion = False
                    sideboard = False
                elif "companion" in lin.lower():
                    commander = False
                    companion = True
                    sideboard = True
                elif "sideboard" in lin.lower():
                    commander = False
                    companion = False
                    sideboard = True
                else:
                    commander = False
                    companion = False
                    sideboard = False
                skip = True
                continue
            dbcard = Card.query.filter_by(id=r['id']).first() #sanity check because sometimes it trys to add things that exist
            if not dbcard:
                dbcard = Card(id=r['id'], name=r['name'], mv=r['cmc'], cost=(r['mana_cost'] if 'mana_cost' in r else r['card_faces'][0]['mana_cost']), identityid=scryfall_color_converter(r['color_identity'])) 
            db.session.add(dbcard)
            db.session.commit()
        else:
            print("FOUND " + dbcard.name)
        
        if dbcard and not skip:
            #add the card entry to deck if relevant (commander etc) and decklist entry
            if commander or (cardparseinfo.group(3) and cardparseinfo.group(3).find('CMDR')):
                if not new_deck.commander:
                    new_deck.commander = dbcard.id
                    new_deck.identityid = dbcard.identityid
                else:
                    new_deck.partner = dbcard.id
                    color1 = Coloridentity.query.filter_by(id=new_deck.identityid).first()
                    color2 = Coloridentity.query.filter_by(id=dbcard.identityid).first()
                    final_color = Coloridentity.query.filter_by(
                        green=(color1.green or color2.green),
                        red=(color1.red or color2.red),
                        blue=(color1.blue or color2.blue),
                        black=(color1.black or color2.black),
                        white=(color1.white or color2.white),
                        ).first()
                    new_deck.identityid = final_color.id
            elif companion:
                new_deck.companion = dbcard.id
            print("Adding " + dbcard.name)
            cardcount = cardparseinfo.group(1)
            if not cardcount:
                cardcount = 1
            else:
                cardcount = re.sub("[^0-9]", "", cardcount)
            new_listentry = Decklist(deckid=new_deck.id, cardid=dbcard.id, iscommander=commander, count=cardcount, iscompanion=companion, issideboard=sideboard)
            db.session.add(new_listentry)
            db.session.commit()

    return jsonify({'message' : 'New deck created', 'deckid': new_deck.id})

@app.route('/deck/v2/<id>', methods=['GET'])
@token_required
@limiter.limit('')
def get_deck_v2(current_user, id):
    deck = Deck.query.filter_by(id=id).first()
    cardlist = [tuple(row) for row in db.session.query(Decklist, Card).join(Card).filter(Decklist.deckid == id).all()]
    if not deck:
        return jsonify({'message' : 'No decks found!'}), 204
    
    legality = get_deck_legality(id)
    
    return jsonify({"deck": deck, "cardlist":cardlist, "legality": legality})

#need to move this somewhere better
def get_deck_legality(id):
    deck = Deck.query.filter_by(id=id).first()
    legal = True
    messages = []
    if not deck:
        return jsonify({'message' : 'No decks found!'})
    
    if not deck.commander:
        legal = False
        messages.append('Missing commander')
    
    cards = db.session.query(Decklist, Card, Coloridentity).select_from(Decklist).join(Card).join(Coloridentity).filter(Decklist.deckid == id).all()
    count = 0
    sideboard_count = 0
    for c in cards:
        if c.Decklist.issideboard:
            sideboard_count += c.Decklist.count
        else:
            count += c.Decklist.count
        if c.Card.banned:
            legal = False
            messages.append('Contains banned card '+str(c.Card.name))
    if deck.companion == '275426c4-c14e-47d0-a9d4-24da7f6f6911':
        if count != 80:
            legal = False
            messages.append('Invalid amount of cards. Expected 80, found '+str(count))
    else:
        if count != 60:
            legal = False
            messages.append('Invalid amount of cards. Expected 60, found '+str(count))
    if sideboard_count and sideboard_count > 5:
            legal = False
            messages.append('Invalid amount of sideboard cards. Expected <= 5, found '+str(sideboard_count))


    return {"legal": legal, "messages": messages}

@app.route('/deck/v2/<id>', methods=['PUT'])
@token_required
@limiter.limit('')
def update_deck_v2(current_user, id):
    data = request.get_json()
    deck = Deck.query.filter_by(id=id).first()
    if not deck:
        return jsonify({'message' : 'No decks found!'}), 204
    
    if not 'prop' in data or not 'val' in data:
        return jsonify({'message' : 'Incomplete data provided!'}), 204
    
    if data['prop'] == 'commander':
        if(deck.commander):
            oldcommander = Decklist.query.filter_by(deckid=id).filter_by(cardid=deck.commander).first()
            oldcommander.iscommander = False
        if not data['val']:
            deck.commander = None
        else:
            deck.commander = data['val']
            cardentry = Decklist.query.filter_by(deckid=id).filter_by(cardid=data['val']).first()
            cardentry.iscommander = True
            if not deck.partner:
                cardinfo = Card.query.filter_by(id=cardentry.cardid).first()
                deck.identityid = cardinfo.identityid
            else:
                cardinfo = db.session.query(Card, Coloridentity).join(Coloridentity).filter(Card.id == cardentry.cardid).all()
                cardinfo2 = db.session.query(Card, Coloridentity).join(Coloridentity).filter(Card.id == deck.partner).all()
                final_color = Coloridentity.query.filter_by(
                        green=(cardinfo[0].Coloridentity.green or cardinfo2[0].Coloridentity.green),
                        red=(cardinfo[0].Coloridentity.red or cardinfo2[0].Coloridentity.red),
                        blue=(cardinfo[0].Coloridentity.blue or cardinfo2[0].Coloridentity.blue),
                        black=(cardinfo[0].Coloridentity.black or cardinfo2[0].Coloridentity.black),
                        white=(cardinfo[0].Coloridentity.white or cardinfo2[0].Coloridentity.white),
                        ).first()
                deck.identityid = final_color.id
    if data['prop'] == 'partner':
        if(deck.partner):
            oldpartner = Decklist.query.filter_by(deckid=id).filter_by(cardid=deck.partner).first()
            oldpartner.ispartner = False
        if not data['val']:
            deck.partner = None
            if deck.commander:
                deckcommander = Card.query.filter_by(id=deck.commander).first()
                deck.identityid = deckcommander.identityid
        else:
            deck.partner = data['val']
            cardentry = Decklist.query.filter_by(deckid=id).filter_by(cardid=data['val']).first()
            cardentry.ispartner = True
            if not deck.commander:
                cardinfo = Card.query.filter_by(id=cardentry.cardid).first()
                deck.identityid = cardinfo.identityid
            else:
                cardinfo = db.session.query(Card, Coloridentity).join(Coloridentity).filter(Card.id == cardentry.cardid).all()
                cardinfo2 = db.session.query(Card, Coloridentity).join(Coloridentity).filter(Card.id == deck.commander).all()
                final_color = Coloridentity.query.filter_by(
                        green=(cardinfo[0].Coloridentity.green or cardinfo2[0].Coloridentity.green),
                        red=(cardinfo[0].Coloridentity.red or cardinfo2[0].Coloridentity.red),
                        blue=(cardinfo[0].Coloridentity.blue or cardinfo2[0].Coloridentity.blue),
                        black=(cardinfo[0].Coloridentity.black or cardinfo2[0].Coloridentity.black),
                        white=(cardinfo[0].Coloridentity.white or cardinfo2[0].Coloridentity.white),
                        ).first()
                deck.identityid = final_color.id
    if data['prop'] == 'companion':
        if(deck.companion):
            oldcompanion = Decklist.query.filter_by(deckid=id).filter_by(cardid=deck.companion).first()
            oldcompanion.iscompanion = False
            oldcompanion.issideboard = False
        if not data['val']:
            deck.companion = None
        else:
            deck.companion = data['val']
            cardentry = Decklist.query.filter_by(deckid=id).filter_by(cardid=data['val']).first()
            cardentry.iscompanion = True
            cardentry.issideboard = True
    if data['prop'] == 'name':
        deck.name = data['val']
    if data['prop'] == 'sideboard' and data['val']:
        cardentry = Decklist.query.filter_by(deckid=id).filter_by(cardid=data['val']).first()
        cardentry.issideboard = True
    if data['prop'] == '-sideboard' and data['val']:
        cardentry = Decklist.query.filter_by(deckid=id).filter_by(cardid=data['val']).first()
        cardentry.issideboard = False
    
    legality = get_deck_legality(id)
    deck.islegal = legality['legal']
    db.session.commit()
    return jsonify({'message' : 'Deck updated'})

@app.route('/removedeck/<id>', methods=['PUT'])
@token_required
@limiter.limit('')
def remove_deck(current_user, id):
    performances = Performance.query.filter_by(deckid = id).first()
    if performances:
        return jsonify({'message' : 'Deck cannot be deleted. It is used in matches'}), 204
    print("stage 2")
    decklist = Decklist.query.filter_by(deckid = id).all()
    for dlentry in decklist:
        db.session.delete(dlentry)
    print("stage 3")
    deck = Deck.query.filter_by(id = id).first()
    print(deck)
    db.session.delete(deck)
    db.session.commit()

    return jsonify({'message' : 'Deck deleted'})

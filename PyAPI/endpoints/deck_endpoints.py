from flask import request, jsonify
from sqlalchemy.orm import aliased
import requests, time, json
import re
import datetime
from helpers import scryfall_color_converter
from models import User, Card, Deck, Decklist, Performance, Coloridentity, Printing
from main import app, limiter, token_required, db

DECKLINE_REGEX = r'^(\d+x?) *([^\(\n\*]+) *(?:\(.*\))? *(?:[\d]+|\w\w\w-\d+)? *(\*CMDR\*)?'

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
    user = data['user'] if 'user' in data else current_user.id

    #commit deck first to use id later
    new_deck = Deck(name=name, userid=user, identityid=1, lastupdated=datetime.datetime.now())
    db.session.add(new_deck)
    db.session.commit()

    commanderRegion = False
    companionRegion = False
    sideboardRegion = False
    skip = False

    for lin in list.split('\n'):
        commander = False
        companion = False
        sideboard = False
        skip = False
        #for each line we need to check if its a card or section identifier then handle appropriately
        cardparseinfo = re.search(DECKLINE_REGEX, lin)
        # group 1: count
        # group 2: cardname
        # group 3: commander flag
        if not cardparseinfo:
            print("COULD NOT PARSE LINE: " + lin)
            if "commander" in lin.lower():
                print("COMMADNERL: " + lin)
                commanderRegion = True
                companionRegion = False
                sideboardRegion = False
            elif "companion" in lin.lower():
                print("COMPANIONL: " + lin)
                commanderRegion = False
                companionRegion = True
                sideboardRegion = True
            elif "sideboard" in lin.lower():
                print("SIDEBOARDL: " + lin)
                commanderRegion = False
                companionRegion = False
                sideboardRegion = True
            else:
                commanderRegion = False
                companionRegion = False
                sideboardRegion = False
            skip = True
            continue

        #try to get from db first
        dbcard = Card.query.filter_by(name=(cardparseinfo.group(2).rstrip().lstrip())).first()
        
        # if we dont find the cardname in our db we fetch from scryfall
        # NOTE: this will also happen sometimes when we have the cardname but it doesnt properly match
        if not dbcard:
            #here we query scryfall for the info
            req = requests.get(url="https://api.scryfall.com/cards/named?exact=" + cardparseinfo.group(2), data=data).content
            time.sleep(0.1) #in order to prevent timeouts we need to throttle to 100ms
            r = json.loads(req)
            print("FETCHED " + cardparseinfo.group(2))
            
            if 'oracle_id' not in r or r['set_type'] == "token":
                #means card no exist probably because its a line defining a card type
                print(cardparseinfo.group(2) + " NOT FOUND")
                skip = True
                continue
            
            dbcard = Card.query.filter_by(id=r['oracle_id']).first() #sanity check because sometimes it trys to add things that exist
            if not dbcard:
                dbcard = Card(id=r['oracle_id'], name=r['name'], typeline=r['type_line'], mv=r['cmc'], cost=(r['mana_cost'] if 'mana_cost' in r else r['card_faces'][0]['mana_cost']), identityid=scryfall_color_converter(r['color_identity'])) 
            db.session.add(dbcard)
            db.session.commit()

            if not Printing.query.filter_by(cardid=dbcard.id).first():
                    print("adding prints")
                    printreq = requests.get(url="https://api.scryfall.com/cards/search?q=oracleid=" + dbcard.id + "&unique=prints").content
                    time.sleep(0.1) #in order to prevent timeouts we need to throttle to 100ms
                    rp = json.loads(printreq)
                    if rp:
                        for p in rp["data"]:
                            if "image_uris" in p:
                                print("once face " + p["id"])
                                new_printing = Printing(id=p["id"], cardid=dbcard.id, cardimage=p["image_uris"]["large"], artcrop=p["image_uris"]["art_crop"])
                                db.session.add(new_printing)
                            else:
                                print("two face")
                                new_printing = Printing(id=p["id"], cardid=dbcard.id, cardimage=p["card_faces"][0]["image_uris"]["large"], artcrop=p["card_faces"][0]["image_uris"]["art_crop"])
                                db.session.add(new_printing)
            db.session.commit()
        else:
            print("FOUND " + dbcard.name)
        
        if dbcard and not skip:
            #add the card entry to deck if relevant (commander etc) and decklist entry
            if commanderRegion or (cardparseinfo.group(3) and cardparseinfo.group(3).find('CMDR')):
                print("CHOSEN COMMANDER")
                if not new_deck.commander:
                    print("CHOSEN COMMANDER 1")
                    commander = True
                    new_deck.commander = dbcard.id
                    new_deck.identityid = dbcard.identityid
                else:
                    print("CHOSEN COMMANDER 2")
                    new_deck.partner = dbcard.id
                    commander = True
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
            elif companionRegion:
                companion = True
                new_deck.companion = dbcard.id
            
            print("Adding " + dbcard.name)
            cardcount = cardparseinfo.group(1)
            
            if not cardcount:
                cardcount = 1
            else:
                cardcount = re.sub("[^0-9]", "", cardcount)
            
            new_listentry = Decklist(deckid=new_deck.id, cardid=dbcard.id, iscommander=commander, count=cardcount, iscompanion=companion, issideboard=sideboardRegion)
            db.session.add(new_listentry)
            db.session.commit()
            new_deck.islegal = get_deck_legality(new_deck.id)['legal']
            db.session.commit()

    return jsonify({'message' : 'New deck created', 'deckid': new_deck.id})

@app.route('/deck/v2/<id>', methods=['GET'])
#@token_required preventing for now
@limiter.limit('')
def get_deck_v2(id):
    deck = Deck.query.filter_by(id=id).first()
    cardlist = [tuple(row) for row in db.session.query(Decklist, Card).join(Card).filter(Decklist.deckid == id).all()]
    if not deck:
        return jsonify({'message' : 'No decks found!'}), 204
    performances = Performance.query.filter_by(deckid=id).all()
    printings = Printing.query.filter_by(cardid=deck.commander).all()
    if not printings and deck.commander:
        print("adding prints")
        printreq = requests.get(url="https://api.scryfall.com/cards/search?q=oracleid=" + deck.commander + "&unique=prints").content
        time.sleep(0.1) #in order to prevent timeouts we need to throttle to 100ms
        rp = json.loads(printreq)
        if rp and "data" in rp:
            for p in rp["data"]:
                if "image_uris" in p:
                    print("once face " + p["id"])
                    new_printing = Printing(id=p["id"], cardid=deck.commander, cardimage=p["image_uris"]["large"], artcrop=p["image_uris"]["art_crop"])
                    db.session.add(new_printing)
                else:
                    print("two face")
                    new_printing = Printing(id=p["id"], cardid=deck.commander, cardimage=p["card_faces"][0]["image_uris"]["large"], artcrop=p["card_faces"][0]["image_uris"]["art_crop"])
                    db.session.add(new_printing)
        db.session.commit()

    printings = Printing.query.filter_by(cardid=deck.commander).all()
    customcards = Card.query.filter_by(custom=True).all()
    legality = get_deck_legality(id)
    
    return jsonify({"deck": deck, "cardlist":cardlist, "legality": legality, "performances": performances, "printings": printings, "customcards": customcards})

@app.route('/decklist/<id>', methods=['GET'])
@limiter.limit('')
def get_decklist(id):
    deck = Deck.query.filter_by(id=id).first()
    cardlist = [tuple(row) for row in db.session.query(Decklist, Card).join(Card).filter(Decklist.deckid == id).all()]
    if not deck:
        return jsonify({'message' : 'No decks found!'}), 204
    
    return jsonify({"deck": deck, "cardlist":cardlist})

@app.route('/deck/<id>/steal', methods=['POST'])
@token_required
@limiter.limit('')
def steal_deck(current_user, id):
    # makes a new deck entry for user and copys decklist from provided decklist
    old_deck = Deck.query.filter_by(id=id).first()
    if not old_deck:
        return jsonify({'message' : 'No decks found!'}), 204
    
    cardlist = [tuple(row) for row in db.session.query(Decklist, Card).join(Card).filter(Decklist.deckid == id).all()]
    
    # create new deck for user using old deck info
    new_deck = Deck(name=old_deck.name + " - Clone", userid=current_user.id, identityid=old_deck.identityid, lastupdated=datetime.datetime.now(), commander=old_deck.commander, partner=old_deck.partner, companion=old_deck.companion, islegal=old_deck.islegal, image=old_deck.image)
    db.session.add(new_deck)
    db.session.commit()
    
    # 0 is decklist data
    # 1 is card data
    for c in cardlist:
        new_listentry = Decklist(deckid=new_deck.id, cardid=c[1].id, iscommander=c[0].iscommander, count=c[0].count, iscompanion=c[0].iscompanion, issideboard=c[0].issideboard)
        db.session.add(new_listentry)
        db.session.commit()

    return jsonify({'message' : 'New deck created', 'deckid': new_deck.id})


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
    if deck.companion == 'e15504a7-2b67-4185-b916-172145f10b19': #yorion oracleid
        if count != 80:
            legal = False
            messages.append('Invalid amount of cards. Expected 80, found '+str(count))
    else:
        if count != 60:
            legal = False
            messages.append('Invalid amount of cards. Expected 60, found '+str(count))
    if sideboard_count and sideboard_count > 7:
            legal = False
            messages.append('Invalid amount of sideboard cards. Expected <= 7, found '+str(sideboard_count))


    return {"legal": legal, "messages": messages}

@app.route('/deck/v2/<id>', methods=['PUT'])
@token_required
@limiter.limit('')
def update_deck_v2(current_user, id):
    data = request.get_json()
    deck = Deck.query.filter_by(id=id).first()
    performances = Performance.query.filter_by(deckid=id).first()
    if not deck:
        return jsonify({'message' : 'No decks found!'}), 204

    if deck.userid != current_user.id and not current_user.admin:
        return jsonify({'message' : 'Not authorized'}), 401
    
    if not 'prop' in data or not 'val' in data:
        return jsonify({'message' : 'Incomplete data provided!'}), 204
    
    if data['prop'] == 'commander':
        if(deck.commander):
            oldcommander = Decklist.query.filter_by(deckid=id).filter_by(cardid=deck.commander).first()
            oldcommander.iscommander = False
        if not data['val']:
            deck.commander = None
            deck.image = None
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
            printing = Printing.query.filter_by(cardid=data['val']).first()
            if printing:
                deck.image = printing.artcrop
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
        if performances:
            return jsonify({'message' : 'Cannot Update Played Deck!'}), 204
        cardentry = Decklist.query.filter_by(deckid=id).filter_by(cardid=data['val']).first()
        cardentry.issideboard = True
    if data['prop'] == '-sideboard' and data['val']:
        if performances:
            return jsonify({'message' : 'Cannot Update Played Deck!'}), 204
        cardentry = Decklist.query.filter_by(deckid=id).filter_by(cardid=data['val']).first()
        cardentry.issideboard = False
    if data['prop'] == 'card' and data['val']:
        if performances:
            return jsonify({'message' : 'Cannot Update Played Deck!'}), 204
        new_listentry = Decklist(deckid=id, cardid=data['val'], count=1, iscommander=False, iscompanion=False, issideboard=False)
        db.session.add(new_listentry)
    if data['prop'] == '-card' and data['val']:
        if performances:
            return jsonify({'message' : 'Cannot Update Played Deck!'}), 204
        cardentry = Decklist.query.filter_by(deckid=id).filter_by(cardid=data['val']).first()
        db.session.delete(cardentry)
    if data['prop'] == 'picpos':
        deck.picpos = data['val']
    if data['prop'] == 'image':
        deck.image = data['val']
    
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
    
    deck = Deck.query.filter_by(id = id).first()
    if not deck:
        return jsonify({'message' : 'No decks found!'}), 204

    if deck.userid != current_user.id and not current_user.admin:
        return jsonify({'message' : 'Not authorized'}), 401

    print("stage 2")
    decklist = Decklist.query.filter_by(deckid = id).all()
    for dlentry in decklist:
        db.session.delete(dlentry)
    db.session.commit()
    print("stage 3")
    print(deck)
    db.session.delete(deck)
    db.session.commit()

    return jsonify({'message' : 'Deck deleted'})

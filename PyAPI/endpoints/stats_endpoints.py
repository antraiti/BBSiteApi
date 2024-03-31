from flask import request, jsonify
from sqlalchemy.orm import aliased
import requests, time, json
import re
import datetime
from dataclasses import dataclass, asdict
from helpers import scryfall_color_converter
from models import User, Card, Deck, Decklist, Performance, Coloridentity, Match, Event
from main import app, limiter, token_required, db

@dataclass
class colorstruct:
    blue: float
    red: float
    green: float
    white: float
    black: float
    colorless: float

    blue = 0
    red = 0
    green = 0
    white = 0
    black = 0
    colorless = 0

@app.route('/stats/user/<id>/simple', methods=['GET'])
@token_required
@limiter.limit('')
def get_user_stats(current_user, id):
    includethemed = request.args.get('themed')
    user = User.query.filter_by(id=id).first()
    if not user:
        return jsonify({'message' : 'No user found!'}), 204
    
    q = db.session.query(Performance, Deck, Coloridentity) \
        .join(Match, Match.id==Performance.matchid) \
        .join(Event, Event.id==Match.eventid)
    
    if not includethemed or includethemed != "true":
        q = q.filter(Event.themed==False)
    
    performances = q.filter(Performance.userid == user.id) \
        .filter(Deck.id==Performance.deckid) \
        .filter(Coloridentity.id==Deck.identityid).all()
    

    matches_played = 0
    matches_won = 0
    average_placement = 0
    color_playcounts = colorstruct()
    color_winrates = colorstruct()

    for p in performances:
        if p[0].placement == None:
            continue
        if p[0].placement == 1:
            matches_won += 1
            color_winrates.blue += p[2].blue
            color_winrates.red += p[2].red
            color_winrates.green += p[2].green
            color_winrates.black += p[2].black
            color_winrates.white += p[2].white
            color_winrates.colorless += p[1].identityid == 1
        color_playcounts.blue += p[2].blue
        color_playcounts.red += p[2].red
        color_playcounts.green += p[2].green
        color_playcounts.black += p[2].black
        color_playcounts.white += p[2].white
        color_playcounts.colorless += p[1].identityid == 1
        matches_played += 1
        average_placement += p[0].placement

    if matches_played > 0:
        average_placement = average_placement/matches_played
    if color_playcounts.blue > 0:
        color_winrates.blue /= color_playcounts.blue
    if color_playcounts.red > 0:
        color_winrates.red /= color_playcounts.red
    if color_playcounts.green > 0:
        color_winrates.green /= color_playcounts.green
    if color_playcounts.black > 0:
        color_winrates.black /= color_playcounts.black
    if color_playcounts.white > 0:
        color_winrates.white /= color_playcounts.white
    if color_playcounts.colorless > 0:
        color_winrates.colorless /= color_playcounts.colorless
    
    return jsonify({"matchesplayed": matches_played, 
                    "matcheswon": matches_won, 
                    "averageplacement": average_placement,
                    "colorplaycount": {"b": color_playcounts.black, "u": color_playcounts.blue,"r": color_playcounts.red,"g": color_playcounts.green,"w": color_playcounts.white,"c": color_playcounts.colorless},
                    "colorwinrates": {"b": color_winrates.black, "u": color_winrates.blue,"r": color_winrates.red,"g": color_winrates.green,"w": color_winrates.white,"c": color_winrates.colorless}})

@app.route('/stats/global/simple', methods=['GET'])
@token_required
@limiter.limit('')
def get_global_stats(current_user):
    includethemed = request.args.get('themed')

    q = db.session.query(Performance, Deck, Coloridentity) \
        .join(Match, Match.id==Performance.matchid) \
        .join(Event, Event.id==Match.eventid)
    
    mq = db.session.query(Match).join(Event, Event.id==Match.eventid)
    
    if not includethemed or includethemed != "true":
        q = q.filter(Event.themed==False)
        mq = mq.filter(Event.themed==False)

    performances = q.filter(Deck.id==Performance.deckid).filter(Coloridentity.id==Deck.identityid).all()
    matches = mq.filter(Match.end!=None).all()

    matches_played = 0
    performance_count = 0
    color_playcounts = colorstruct()
    color_winrates = colorstruct()
    matches_played = len(matches)
    matchtime = 0

    for m in matches:
        matchtime += ((m.end) - (m.start)).seconds
    matchtime/=matches_played


    for p in performances:
        if p[0].placement == None:
            continue
        if p[0].placement == 1:
            color_winrates.blue += p[2].blue
            color_winrates.red += p[2].red
            color_winrates.green += p[2].green
            color_winrates.black += p[2].black
            color_winrates.white += p[2].white
            color_winrates.colorless += p[1].identityid == 1
        color_playcounts.blue += p[2].blue
        color_playcounts.red += p[2].red
        color_playcounts.green += p[2].green
        color_playcounts.black += p[2].black
        color_playcounts.white += p[2].white
        color_playcounts.colorless += p[1].identityid == 1
        performance_count += 1

    if color_playcounts.blue > 0:
        color_winrates.blue /= color_playcounts.blue
    if color_playcounts.red > 0:
        color_winrates.red /= color_playcounts.red
    if color_playcounts.green > 0:
        color_winrates.green /= color_playcounts.green
    if color_playcounts.black > 0:
        color_winrates.black /= color_playcounts.black
    if color_playcounts.white > 0:
        color_winrates.white /= color_playcounts.white
    if color_playcounts.colorless > 0:
        color_winrates.colorless /= color_playcounts.colorless
    
    return jsonify({"matchesplayed": matches_played,
                    "averagematchsize": performance_count/matches_played,
                    "averagematchtime": matchtime,
                    "colorplaycount": {"b": color_playcounts.black, "u": color_playcounts.blue,"r": color_playcounts.red,"g": color_playcounts.green,"w": color_playcounts.white,"c": color_playcounts.colorless},
                    "colorwinrates": {"b": color_winrates.black, "u": color_winrates.blue,"r": color_winrates.red,"g": color_winrates.green,"w": color_winrates.white,"c": color_winrates.colorless}})

@app.route('/stats/watchlist', methods=['GET'])
@token_required
@limiter.limit('')
def get_watchlist_stats(current_user):
        performances = db.session.query(Performance, Deck, Decklist, Card).filter(Deck.id==Performance.deckid).filter(Decklist.deckid==Deck.id).filter(Card.id==Decklist.cardid).all()
        performances = list(filter(lambda x: x[3].watchlist==1, performances))
        watchlist = Card.query.filter_by(watchlist=1).all()
        res = []
        for wcard in watchlist:
            playcount = len(list(filter(lambda x: x[3].id==wcard.id, performances)))
            wincount = len(list(filter(lambda x: x[3].id==wcard.id and x[0].placement=="1", performances)))
            averageplacement = 0
            for p in list(filter(lambda x: x[3].id==wcard.id, performances)):
                if p[0].placement:
                    averageplacement += p[0].placement
            if playcount > 0:
                averageplacement /= playcount
            res.append({"id": wcard.id, "name": wcard.name, "playcount":playcount, "wincount": wincount, "average": averageplacement})

        return jsonify({"data": res})

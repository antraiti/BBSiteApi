from flask import request, jsonify
from sqlalchemy.orm import aliased
from helpers import scryfall_color_converter
from models import Theme
from main import app, limiter, token_required, db

@app.route('/themes', methods=['GET'])
@token_required
@limiter.limit('')
def get_themes(current_user):
    themes = Theme.query.all()
    if not themes:
        return jsonify({'message' : 'No themes found!'}), 204
    
    return jsonify(themes)
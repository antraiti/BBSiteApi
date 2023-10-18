from flask import jsonify
from models import Coloridentity
from main import app, limiter

@app.route('/colors', methods=['GET'])
@limiter.limit('')
def get_coloridentities():
    colors = Coloridentity.query.all()
    return jsonify(colors)
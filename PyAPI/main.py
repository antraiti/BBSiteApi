from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from pathlib import Path
import jwt
import configparser
from functools import wraps
from models import *

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["60 per minute"], #this should be reduced as we optimize the pages (10 per min probably with an added hour or day amount cap)
    storage_uri="memory://",
)

CORS(app)
config = configparser.ConfigParser()
config.read(Path(__file__).with_name('config.ini'))

app.config['SECRET_KEY'] = config['SECURITY']['SECRET_KEY']
app.config['SQLALCHEMY_DATABASE_URI'] = config['DATABASE']['CONNECTION']

db.init_app(app)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

        if not token:
            return jsonify({'message' : 'Token is missing!'}), 401
        try: 
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.filter_by(publicid=data['publicid']).first()
        except:
            return jsonify({'message' : 'Token is invalid!'}), 401

        return f(current_user, *args, **kwargs)

    return decorated

from endpoints.login_endpoints import *
from endpoints.user_endpoints import *
from endpoints.deck_endpoints import *
from endpoints.event_endpoints import *
from endpoints.match_endpoints import *
from endpoints.performance_endpoints import *
from endpoints.color_endpoints import *
from endpoints.card_endpoints import *

if __name__ == "__main__":
    app.run(debug=True)

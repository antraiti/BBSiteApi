from werkzeug.security import generate_password_hash
from flask import Flask, request, jsonify

app = Flask(__name__)

app.config['SECRET_KEY'] = ''
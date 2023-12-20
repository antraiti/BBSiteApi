from werkzeug.security import generate_password_hash
from flask import Flask, request, jsonify
import configparser
from pathlib import Path

app = Flask(__name__)
config = configparser.ConfigParser()
config.read(Path(__file__).with_name('config.ini'))
app.config['SECRET_KEY'] = config['SECURITY']['SECRET_KEY']

print(generate_password_hash(''))
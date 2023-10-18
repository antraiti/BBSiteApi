from flask import request, jsonify
from werkzeug.security import generate_password_hash
import uuid
from models import User
from main import app, limiter, token_required, db

@app.route('/user', methods=['POST'])
@token_required
@limiter.limit('')
def create_user(current_user):
    if not current_user.admin:
        return jsonify({'message' : 'Lacking Permissions'})

    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()

    if user:
        return jsonify({'message' : 'User already exists'})

    hashed_password = generate_password_hash(data['password'])

    new_user = User(username=data['username'], hash=hashed_password, publicid=str(uuid.uuid4()))
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message' : 'New user created'})

@app.route('/user/<username>', methods=['PUT'])
@token_required
@limiter.limit('')
def update_user(current_user, username):
    if not current_user.admin:
        return jsonify({'message' : 'Lacking Permissions'})

    data = request.get_json()
    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify({'message' : 'No user found!'})

    #Handle changes here

    db.session.commit()

    return jsonify({'message' : 'Updated user'})

@app.route('/user', methods=['GET'])
@limiter.limit('')
def get_users():
    users = User.query.all()

    if not users:
         return jsonify({'message' : 'No users found!'})

    return jsonify(users)
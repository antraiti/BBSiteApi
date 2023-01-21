from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SECRET_KEY'] = 'addsomething'
app.config['SQLALCHEMY_DATABASE_URI'] = ''

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True)
    hash = db.Column(db.String(255))
    salt = db.Column(db.String(255))

@app.route('/user', methods=['POST'])
def create_user():
    data = request.get_json()

    hashed_password = data['password']

    new_user = User(username=data['username'], hash=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message' : 'New user created'})

@app.route('/user/<username>', methods=['PUT'])
def update_user(username):
    data = request.get_json()

    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify({'message' : 'No user found!'})

    user.salt = "yoyo"
    db.session.commit()

    return jsonify({'message' : 'Updated user'})

if __name__ == "__main__":
    app.run(debug=True)


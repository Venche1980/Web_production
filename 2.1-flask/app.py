from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Конфигурация базы данных PostgreSQL
DATABASE_CONFIG = {
    'dbname': 'flask_01',
    'user': 'postgres',
    'password': '123',
    'host': 'localhost',
    'port': 5432
}

app = Flask(__name__)
app.config[
    'SQLALCHEMY_DATABASE_URI'] = f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['dbname']}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# Модели
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class Advertisement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# Создание таблиц
with app.app_context():
    db.create_all()


# Простая функция для проверки авторизации
def check_auth(email, password):
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password_hash, password):
        return user
    return None


# Регистрация пользователя
@app.route('/register', methods=['POST'])
def register():
    data = request.json

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Пользователь уже существует'}), 400

    user = User(
        email=data['email'],
        password_hash=generate_password_hash(data['password'])
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'Пользователь создан'}), 201


# Создание объявления
@app.route('/advertisements', methods=['POST'])
def create_ad():
    data = request.json

    # Простая авторизация через заголовки
    email = request.headers.get('User-Email')
    password = request.headers.get('User-Password')

    user = check_auth(email, password)
    if not user:
        return jsonify({'error': 'Неверная авторизация'}), 401

    ad = Advertisement(
        title=data['title'],
        description=data['description'],
        owner_id=user.id
    )

    db.session.add(ad)
    db.session.commit()

    return jsonify({
        'id': ad.id,
        'title': ad.title,
        'description': ad.description,
        'created_at': ad.created_at.isoformat(),
        'owner_id': ad.owner_id
    }), 201


# Получение объявления
@app.route('/advertisements/<int:ad_id>', methods=['GET'])
def get_ad(ad_id):
    ad = Advertisement.query.get(ad_id)
    if not ad:
        return jsonify({'error': 'Объявление не найдено'}), 404

    return jsonify({
        'id': ad.id,
        'title': ad.title,
        'description': ad.description,
        'created_at': ad.created_at.isoformat(),
        'owner_id': ad.owner_id
    })


# Редактирование объявления
@app.route('/advertisements/<int:ad_id>', methods=['PUT'])
def update_ad(ad_id):
    data = request.json

    # Проверка авторизации
    email = request.headers.get('User-Email')
    password = request.headers.get('User-Password')

    user = check_auth(email, password)
    if not user:
        return jsonify({'error': 'Неверная авторизация'}), 401

    ad = Advertisement.query.get(ad_id)
    if not ad:
        return jsonify({'error': 'Объявление не найдено'}), 404

    # Проверка прав владельца
    if ad.owner_id != user.id:
        return jsonify({'error': 'Нет прав для редактирования'}), 403

    ad.title = data['title']
    ad.description = data['description']

    db.session.commit()

    return jsonify({
        'id': ad.id,
        'title': ad.title,
        'description': ad.description,
        'created_at': ad.created_at.isoformat(),
        'owner_id': ad.owner_id
    })


# Удаление объявления
@app.route('/advertisements/<int:ad_id>', methods=['DELETE'])
def delete_ad(ad_id):
    # Проверка авторизации
    email = request.headers.get('User-Email')
    password = request.headers.get('User-Password')

    user = check_auth(email, password)
    if not user:
        return jsonify({'error': 'Неверная авторизация'}), 401

    ad = Advertisement.query.get(ad_id)
    if not ad:
        return jsonify({'error': 'Объявление не найдено'}), 404

    # Проверка прав владельца
    if ad.owner_id != user.id:
        return jsonify({'error': 'Нет прав для удаления'}), 403

    db.session.delete(ad)
    db.session.commit()

    return jsonify({'message': 'Объявление удалено'})


if __name__ == '__main__':
    app.run(debug=True)
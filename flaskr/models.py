from flaskr import db, login_manager
from flask_bcrypt import generate_password_hash, check_password_hash
from flask_login import UserMixin, current_user
from sqlalchemy.orm import aliased

from datetime import datetime, timedelta
from uuid import uuid4

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

class User(UserMixin, db.Model):

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True)
    email = db.Column(db.String(64), unique=True, index=True)
    password = db.Column(
        db.String(128),
        default=generate_password_hash('flaskpractice')
    )
    picture_path = db.Column(db.Text)
    is_active = db.Column(db.Boolean, unique=False, default=False)
    create_at = db.Column(db.DateTime, default=datetime.now)
    update_at = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, username, email):
        self.username = username
        self.email = email

    # emailに該当するユーザを取得
    @classmethod
    def select_user_by_email(cls, email):
        return cls.query.filter_by(email=email).first()

    # パスワードが正しいか確認
    def validate_password(self, password):
        return check_password_hash(self.password, password)

    # dbにユーザを追加
    def create_new_user(self):
        db.session.add(self)

    # idに該当するユーザを取得
    @classmethod
    def select_user_by_id(cls, id):
        return cls.query.get(id)

    # パスワードを保存し、アクティブ状態にする
    def save_new_password(self, new_password):
        self.password = generate_password_hash(new_password)
        self.is_active = True

# パスワードリセット時に利用する
class PasswordResetToken(db.Model):

    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(
        db.String(64),
        unique=True,
        index = True,
        server_default=str(uuid4)
    )
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    expire_at = db.Column(db.DateTime, default=datetime.now)
    create_at = db.Column(db.DateTime, default=datetime.now)
    update_at = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, token, user_id, expire_at):
        self.token = token
        self.user_id = user_id
        self.expire_at = expire_at

    @classmethod
    def publish_token(cls, user):
        # パスワード設定用のURLを生成
        token = str(uuid4())
        new_token = cls(
            token,
            user.id,
            datetime.now() + timedelta(days=1)
        )
        db.session.add(new_token)
        return token

    # tokenが一致するユーザIDを取得
    @classmethod
    def get_user_id_by_token(cls, token):
        now = datetime.now()
        record = cls.query.filter_by(token=str(token)).filter(cls.expire_at > now).first()
        if record:
            return record.user_id
        else:
            return None

    # 利用を終えたtokenを削除
    @classmethod
    def delete_token(cls, token):
        cls.query.filter_by(token=str(token)).delete()

# ボイス投稿時に利用する
class Voice(db.Model):

    __tablename__ = 'voices'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64))
    picture_path = db.Column(db.Text)
    voice = db.Column(db.Text)
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    create_at = db.Column(db.DateTime, default=datetime.now)
    update_at = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, from_user_id, title, picture_path, voice):
        self.from_user_id = from_user_id
        self.title = title
        self.picture_path = picture_path
        self.voice = voice

    def create_voice(self):
        db.session.add(self)

    def delete_voice(self):
        db.session.delete(self)

    # idに該当するボイスを取得
    @classmethod
    def select_voice_by_id(cls, id):
        return cls.query.get(id)

    # ユーザIDを条件にボイスを全て取得
    @classmethod
    def select_by_from_user_id_all(cls, id):
        return cls.query.filter_by(from_user_id=id).all()



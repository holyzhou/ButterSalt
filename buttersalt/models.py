from . import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app
from flask_login import UserMixin


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), unique=True, nullable=False)
    confirmed = db.Column(db.Boolean, default=0)
    email = db.Column(db.String(128), unique=True, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expires_in=expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = 1
        db.session.add(self)
        db.session.commit()
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        db.session.commit()
        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        db.session.add(self)
        db.session.commit()
        return True

    def __repr__(self):
        return "<Users" \
               "(username=%s, password=%s, email=%s, role=%s)>" % \
               (self.username, self.password, self.email, self.role)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return '<Role %r>' % self.name


class UserRole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    salt_username = db.Column(db.String(128))
    salt_password = db.Column(db.String(128))

    def __repr__(self):
        return "<UserRole" \
               "(name=%s, salt_username=%s, salt_password=%s)>" % \
               (self.name, self.salt_username, self.salt_password, )


class UserRoleAuthority(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    role = db.Column(db.Integer, db.ForeignKey('user_role.id'))
    resources = db.Column(db.String(128), nullable=False)

    def __repr__(self):
        return '<authority %r in role_id %r>' % (self.name, self.role)


class SaltExecuteHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tgt = db.Column(db.String(128), nullable=False)
    fun = db.Column(db.String(128), nullable=False)
    args = db.Column(db.String(128))
    kwargs = db.Column(db.String(128))
    user = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return "<SaltExecuteHistory" \
               "(tgt=%s, fun=%s, args=%s, kwargs=%s, user=%s)>" % \
               (self.tgt, self.fun, self.args, self.kwargs, self.user)

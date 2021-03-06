from sqlalchemy import UniqueConstraint

from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime, timedelta
from hashlib import md5
from datetime import datetime
from sqlalchemy.dialects.postgresql.json import JSONB



@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(240), index=False, unique=False)
    date_posted = db.Column(db.DateTime, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                        nullable=False)

    likes = db.relationship('PostLike', backref='post', lazy='dynamic')


    def get_user(self):
        return User.query.get(
            self.user_id
        )

    def get_date_posted(self):
        if self.date_posted:
            return self.date_posted.strftime("%b %d %Y %H:%M:%S")
        else:
            return ''

    def __repr__(self):
        return '<Post {}>'.format(self.body)

    def __init__(self, body, author):
        self.body = body
        self.author = author
        self.date_posted = datetime.now()


connections = db.Table('connections',
                       db.Column('sender_id', db.Integer, db.ForeignKey('users.id')),
                       db.Column('recipient_id', db.Integer, db.ForeignKey('users.id')),
                       db.Column('are_connected', db.Boolean, default=False)
                       )


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    github = db.Column(db.String(64), index=True, unique=False)
    password_hash = db.Column(db.String(128))
    authentication = db.Column(db.Boolean, default=False)
    posts = db.relationship('Post', backref='author', lazy='dynamic', cascade='all, delete')
    languages = db.Column(JSONB, default=None)
    repos = db.Column(JSONB, default=None)
    connected = db.relationship(
        'User', secondary=connections,
        primaryjoin=(connections.c.sender_id == id),
        secondaryjoin=(connections.c.recipient_id == id),
        backref=db.backref('connections', lazy='dynamic'), lazy='dynamic')
    liked = db.relationship(
        'PostLike',
        foreign_keys='PostLike.user_id',
        backref='user', lazy='dynamic')

    def __init__(self, username, email):
        self.username = username
        self.email = email

    def __repr__(self):
        return f"<User: {self.username}>"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def request(self, users):
        if not self.is_requested(users):
            self.connected.append(users)

    def is_requested(self, users):
        return self.connected.filter(
            connections.c.recipient_id == users.id).count() > 0

    def get_requests(self):
        requests = User.query.join(connections, (
                connections.c.recipient_id == self.id)).filter(
                connections.c.sender_id == User.id).filter(
                connections.c.are_connected == "false"
                )
        return requests

    def search_connections(self, search):
        connections_received = User.query.join(connections, (
                connections.c.recipient_id == self.id)).filter(
                connections.c.sender_id == User.id).filter(
                connections.c.are_connected == "true"
                )
        connections_sent = User.query.join(connections, (
                connections.c.recipient_id == User.id)).filter(
                connections.c.sender_id == self.id).filter(
                connections.c.are_connected == "true"
                )
        all_connections = connections_received.union(connections_sent)
        search_result = all_connections.filter(User.username.contains(search)).all()
        return search_result

    def is_connected(self, users):
        return self.connected.filter(
            connections.c.recipient_id == users.id).filter(connections.c.are_connected == "true").count() > 0.

    def remove_connection_recipient(self, users):
        update = connections.delete().where(
            connections.c.recipient_id == self.id).where(
            connections.c.sender_id == users.id)
        db.session.execute(update)

    def remove_connection_sender(self, users):
        update = connections.delete().where(
            connections.c.recipient_id == users.id).where(
            connections.c.sender_id == self.id)
        db.session.execute(update)

    def accept_request(self, users):
        update_statement = connections.update().where(
            connections.c.recipient_id == self.id).where(
            connections.c.sender_id == users.id).values(are_connected = True)
        db.session.execute(update_statement)

    def decline_request(self, users):
        update = connections.delete().where(
            connections.c.recipient_id == self.id).where(
            connections.c.sender_id == users.id)
        db.session.execute(update)
    
    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)

    def own_posts(self):
        own = Post.query.filter_by(user_id=self.id)
        return own.order_by(Post.date_posted.desc())

    def connected_posts(self):
        connections_sent_posts = Post.query.join(
            connections, (connections.c.recipient_id == Post.user_id)).filter(
            connections.c.sender_id == self.id, connections.c.are_connected == "true")
        connections_received_posts = Post.query.join(
            connections, (connections.c.sender_id == Post.user_id)).filter(
            connections.c.recipient_id == self.id, connections.c.are_connected == "true")
        own_posts = Post.query.filter_by(user_id=self.id)
        return connections_sent_posts.union(own_posts).union(connections_received_posts).order_by(Post.date_posted.desc())

    def like_post(self, post):
        if not self.has_liked_post(post):
            like = PostLike(user_id=self.id, post_id=post.id)
            db.session.add(like)

    def unlike_post(self, post):
        if self.has_liked_post(post):
            PostLike.query.filter_by(
                user_id=self.id,
                post_id=post.id).delete()

    def has_liked_post(self, post):
        return PostLike.query.filter(
            PostLike.user_id == self.id,
            PostLike.post_id == post.id).count() > 0


class PostLike(db.Model):
    __tablename__ = 'post_like'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))

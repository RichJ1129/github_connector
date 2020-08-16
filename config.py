import os
from boto.s3.connection import S3Connection




class Config(object):
    POSTS_PER_PAGE = 3
    CONNECTIONS_PER_PAGE = 5
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key'
    DATABASE_URL = os.environ.get('DATABASE_URL', None)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

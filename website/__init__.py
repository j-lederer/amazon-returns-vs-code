from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from os import path
# from flask_login import LoginManager
from flask_migrate import Migrate
import os
# from sqlalchemy import URL
import sqlalchemy
import stripe
from flask_security import Security, hash_password, SQLAlchemySessionUserDatastore, SQLAlchemyUserDatastore
from redis import Redis
import rq
import rq_dashboard

from .utils import make_celery
from celery.schedules import crontab

from flask_sqlalchemy import SQLAlchemy
# from sqlalchemy.pool import NullPool
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

db = SQLAlchemy()

def create_app():
  app = Flask(__name__)

  @app.before_request
  def log_session_info():
      # Log session ID and user-specific information
      session_id = session.get('_id', 'no-session-id')
      user_id = session.get('user_id', 'anonymous')
      logging.info(f"Current Session ID: {session_id}, User ID: {user_id}")
  
  app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
  app.config['SESSION_COOKIE_NAME'] = os.environ['SESSION_COOKIE_NAME']
  app.config['SESSION_COOKIE_SECURE'] = True
  app.config['SESSION_COOKIE_HTTPONLY'] = True
  app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
  app.config["CELERY_CONFIG"] = {"broker_url": os.environ['REDIS_URL'], "result_backend": os.environ['REDIS_URL'], "beat_schedule": {
                                    "every-day-at 12am" : {
                                        "task": "website.views.every_day",
                                      # 'schedule':20
                                        "schedule": crontab(hour=4, minute=0, day_of_week='0-6') #timezone is 5 hours ahead of est. It is UTC. So 5 will be 12am
                                        #"args": (1, 2) 
                                    }
                                }}
  
  app.config['RQ_DASHBOARD_REDIS_URL'] =os.environ['REDIS_URL']
  app.config.from_object(rq_dashboard.default_settings)
  rq_dashboard.web.setup_rq_connection(app)
  app.register_blueprint(rq_dashboard.blueprint, url_prefix="/rq")
  # url_object = URL.create(
  # #sqlUrl = sqlalchemy.engine.url.URL(
  #   drivername="mysql+pymysql",
  #   username=os.getenv("DB_USER"),
  #   password=os.getenv("DB_PASSWORD"),
  #   host=os.getenv("DB_HOST"),
  #   database=os.getenv("DB_DATABASE"),
  #   query={
  #     "ssl_ca":"/etc/ssl/cert.pem"},
  # )
  app.config['SQLALCHEMY_DATABASE_URI'] =os.environ['RAILWAY_DB_CONNECTION_STRING']
  app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
  # app.config['SQLALCHEMY_POOL_RECYCLE'] = 299
  # app.config['SQLALCHEMY_POOL_TIMEOUT'] = 20
  app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_use_lifo": True}
  # app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"poolclass": NullPool}
  # app.config['STRIPE_PUBLIC_KEY'] = os.environ['STRIPE_TEST_PUBLIC_KEY']
  app.config['STRIPE_PUBLIC_KEY'] = os.environ['STRIPE_PUBLIC_KEY']
  # app.config['STRIPE_SECRET_KEY'] = os.environ['STRIPE_TEST_SECRET_KEY'] 
  app.config['STRIPE_SECRET_KEY'] = os.environ['STRIPE_SECRET_KEY'] 
  app.redis = Redis.from_url(os.environ['REDIS_URL'])
  app.task_queue = rq.Queue('amazon-returns-task-queue', connection=app.redis)
  #os.environ[
  #   'DB2'] + '?ssl_ca=website/addedExtras/cacert-2023-05-30.pem'
  #/etc/ssl/cert.pem'
  # app.config['SQLALCHEMY_DATABASE_URI'] = url_object
  #app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
  db.init_app(app)
  migrate = Migrate(app, db)
  stripe.api_key = app.config['STRIPE_SECRET_KEY']
  from .views import views
  from .auth import auth
  from .stripePay import stripePay
  from .connectAmazon import connectAmazon

  app.register_blueprint(views, url_prefix='/')
  app.register_blueprint(auth, url_prefix='/')
  app.register_blueprint(stripePay, url_prefix='/')
  app.register_blueprint( connectAmazon, url_prefix='/')
  
  celery = make_celery(app)
  celery.set_default()

  
  from .models import User, Role

  with app.app_context():
    db.create_all()

  # login_manager = LoginManager()
  # login_manager.login_view = 'auth.login'
  # login_manager.init_app(app)

  # @login_manager.user_loader
  # def load_user(id):
  #   return User.query.get(int(id))

  
  #Setup Flask-Security
  app.config['SECURITY_PASSWORD_SALT'] = os.environ.get("SECURITY_PASSWORD_SALT")
  # user_datastore = SQLAlchemySessionUserDatastore(db.session, User, Role)
  user_datastore = SQLAlchemyUserDatastore(db, User, Role)
  app.security = Security(app, user_datastore)

  # from .auth import auth
  # from .auth import init_user_datastore
  # init_user_datastore(user_datastore)
  app.config['USER_DATASTORE'] = SQLAlchemyUserDatastore(db, User, Role)

  from flask_mailman import Mail

  app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER")
  app.config["MAIL_PORT"] = os.getenv("MAIL_PORT")
  app.config["MAIL_USE_SSL"] = False
  app.config["MAIL_USE_TLS"] = True
  app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
  app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
  mail = Mail(app)

  return app, celery

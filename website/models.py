from . import db
# from flask_login import UserMixin
from sqlalchemy.sql import func
from flask_security import   UserMixin, RoleMixin
import redis
import rq
from flask import current_app
import json
from time import time

# class Note(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     data = db.Column(db.String(10000))
#     date = db.Column(db.DateTime(timezone=True), default=func.now())
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
class Addresses(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  OrderID = db.Column(db.String(250))
  Address = db.Column(db.String(500))
  date = db.Column(db.DateTime(timezone=True), default=func.now())
  user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))


class All_return_details(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  tracking_id = db.Column(db.String(250))
  item_name = db.Column(db.String(500))
  sku = db.Column(db.String(500))
  return_quantity = db.Column(db.String(500))
  refund_amount = db.Column(db.String(500))
  order_id = db.Column(db.String(500))
  order_quantity = db.Column(db.String(500))
  asin = db.Column(db.String(500))
  Inventory = db.Column(db.String(500))
  reason_returned = db.Column(db.String(500))
  date = db.Column(db.DateTime(timezone=True), default=func.now())
  user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))


class Current_return_to_display(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  tracking_id = db.Column(db.String(250))
  item_name = db.Column(db.String(500))
  sku = db.Column(db.String(500))
  return_quantity = db.Column(db.String(500))
  refund_amount = db.Column(db.String(500))
  order_id = db.Column(db.String(500))
  order_quantity = db.Column(db.String(500))
  asin = db.Column(db.String(500))
  Inventory = db.Column(db.String(500))
  reason_returned = db.Column(db.String(500))
  date = db.Column(db.DateTime(timezone=True), default=func.now())
  user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))


class Tracking_id_to_search(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  tracking_id = db.Column(db.String(250))
  date = db.Column(db.DateTime(timezone=True), default=func.now())
  user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))


class Tracking_ids(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  tracking = db.Column(db.String(250))
  SKU = db.Column(db.String(250))
  return_quantity = db.Column(db.String(250))
  date = db.Column(db.DateTime(timezone=True), default=func.now())
  user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))


class User(db.Model, UserMixin):
  id = db.Column(db.Integer, primary_key=True)
  email = db.Column(db.String(150), unique=True)
  password = db.Column(db.String(150))
  first_name = db.Column(db.String(150))
  date_joined = db.Column(db.DateTime(timezone=True), default=func.now())
  status = db.Column(db.String(150))
  refresh_token = db.Column(db.String(3000))
  token_expiration = db.Column(db.DateTime(timezone=True), default=None)
  restricted = db.Column(db.String(150))
  delete_request = db.Column(db.String(150))
  fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)
  active = db.Column(db.Boolean())
  confirmed_at = db.Column(db.DateTime(timezone=True))
  addresses = db.relationship('Addresses', backref='addresses_ref', passive_deletes=True)
  all_return_details = db.relationship('All_return_details',
                                       backref='all_return_details_ref', passive_deletes=True)
  current_return_to_display = db.relationship(
    'Current_return_to_display', backref='current_return_to_display_ref', passive_deletes=True)
  tracking_id_to_search = db.relationship('Tracking_id_to_search',
                                          backref='tracking_id_to_search_ref', passive_deletes=True )
  tracking_ids = db.relationship('Tracking_ids', backref='tracking_ids_ref', passive_deletes=True)
  stripecustomer = db.relationship('Stripecustomer', backref='stripecustomer_ref', passive_deletes=True)
  tasks = db.relationship('Task', backref='user', lazy='dynamic')
  roles = db.relationship('Role', secondary='roles_users', backref=db.backref('users', lazy='dynamic'),
passive_deletes=True)
  notifications = db.relationship('Notification', backref='user',
                                    lazy='dynamic')

  
  def launch_task(self, name, description, *args, **kwargs):
        rq_job = current_app.task_queue.enqueue('website.views.' + name, self.id,
                                                *args, **kwargs)
        task = Task(id=rq_job.get_id(), name= name, description=description,
                    user=self)
        db.session.add(task)
        return task

  def get_tasks_in_progress(self):
        return Task.query.filter_by(user=self, complete=False).all()

  def get_task_in_progress(self, name):
        return Task.query.filter_by(name=name, user=self,
                                    complete=False).first()
  def add_notification(self, name, data):
        # self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n
  

# class RolesUsers(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column('user_id', db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
#     role_id = db.Column('role_id', db.Integer, db.ForeignKey('role.id', ondelete='CASCADE'))

roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)


class Deleted_users(db.Model, UserMixin):
  id = db.Column(db.Integer, primary_key=True)
  email = db.Column(db.String(150))
  password = db.Column(db.String(150))
  first_name = db.Column(db.String(150))
  date_joined = db.Column(db.DateTime(timezone=True), default=func.now())
  status = db.Column(db.String(150))

class Stripecustomer(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    stripeCustomerId = db.Column(db.String(255), nullable=False)
    stripeSubscriptionId = db.Column(db.String(255), nullable=False)

class Suggestions(db.Model):
  id = db.Column(db.Integer, primary_key=True, autoincrement=True)
  suggestion = db.Column(db.String(10000), nullable=False)
  userid = db.Column(db.String(200), nullable=False)
  date = db.Column(db.DateTime(timezone=True), default=func.now())

class Task(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    complete = db.Column(db.Boolean, default=False)

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None else -1



class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))
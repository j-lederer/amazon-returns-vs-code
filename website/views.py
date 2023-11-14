from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from .database import engine, load_queue_from_db, load_all_return_details_from_db, load_tracking_id_to_search, delete_trackingID_from_queue_db, add_tracking_id_to_queue, refresh_all_return_data_in_db, load_current_return_to_display_from_db, add_current_return_to_display_to_db, delete_whole_tracking_id_queue, delete_current_return_to_display_from_db, delete_tracking_id_to_search, add_tracking_id_to_search, check_if_track_in_queue, delete_current_return_to_display_from_db, refresh_addresses_in_db, load_address_from_db, load_users_from_db, load_deleted_users_from_db, delete_user_from_db, delete_deleted_user_from_db, clear_all_users_from_db, clear_all_deleted_users_from_db, add_refresh_token, get_refresh_token, load_restricted, add_request_to_delete_user, load_all_stripe_customers, add_suggestion, delete_refresh_token_and_expiration, load_jobs_from_db, load_history_from_db_descending_order, add_queue_to_task_details, load_my_task_trackers_from_db, delete_job_db, get_info_job_from_db, load_task_details_from_db

from .models import User, Notification, Stripecustomer, Task, My_task_tracker
from .amazonAPI import get_all_Returns_data, increaseInventory, checkInventory, checkInventoryIncrease, get_addresses_from_GetOrders

from flask import Blueprint, render_template, request, flash, jsonify, send_file, make_response, current_app
# from flask_login import login_required, current_user
from flask_security import login_required, current_user
import stripe
from . import db
import json
from io import BytesIO
import os
from collections import Counter
from datetime import datetime
import re

from .download_pdf_queue import download_queue_data
from .download_pdf_inventoryChange import download_queue_and_inventory_change_data
from .download_inventory_to_change import download_inventory_change

# from .tasks import print_numbers, increase_inventory_task

from celery import shared_task
from celery.contrib.abortable import AbortableTask
from celery.result import AsyncResult

from sqlalchemy.exc import PendingRollbackError, OperationalError


views = Blueprint('views', __name__)



@views.route('/', methods=['POST', 'GET'])
@login_required
def home(): 
  # print(current_user)
  # print(current_user.id)  #returnDetails = load_returnDetails_from_db()
  
  All_Return_Details = load_all_return_details_from_db(current_user.id)
  tracking_id=None
  return_details_to_display=None
  Address='No Data'
  queueChecker = "NO"
  
 
  
  if load_tracking_id_to_search(current_user.id):
    tracking_id = load_tracking_id_to_search(current_user.id)
    if check_if_track_in_queue(tracking_id, current_user.id):
      queueChecker = "YES"
    
    addresses= load_address_from_db(current_user.id)

  
    add_current_return_to_display_to_db(tracking_id, current_user.id)
  return_details_to_display = load_current_return_to_display_from_db(current_user.id)
  queue = load_queue_from_db(current_user.id)
  print("TOKEN EXPIRATION:")
  print (current_user.token_expiration )
  if current_user.token_expiration is not None:
    current_date = datetime.now()
    token_expiration =  current_user.token_expiration
    if (token_expiration < current_date):
        delete_refresh_token_and_expiration (current_user.id)
  
  
  customer = Stripecustomer.query.filter_by(user_id=current_user.id).order_by(Stripecustomer.id.desc()).first()
  subscription = None
  if customer:
        subscription = stripe.Subscription.retrieve(customer.stripeSubscriptionId)
        product = stripe.Product.retrieve(subscription.plan.product)
        context = {
            "subscription": subscription,
            "product": product,
        }
    
  if(not load_restricted(current_user.id)):
    if(get_refresh_token (current_user.id) and current_user.token_expiration is not None):
      if (subscription and (subscription.status == 'active' or subscription.status == 'trialing')) or (current_user.email == os.environ['ADMIN_EMAIL']):
        if ((return_details_to_display and tracking_id and customer) ):  #if they exist
          print(return_details_to_display)
          orderID = return_details_to_display['order_id']
          for data in addresses:
            if data['OrderID'] == orderID:
              Address = data['Address']
              #print(Address)
          return render_template('home.html', tasks=queue, passed_value = return_details_to_display, tracking_id=tracking_id, queue_checker=queueChecker, address=Address,  user=current_user, **context)
        elif( return_details_to_display and tracking_id and current_user.email == os.environ['ADMIN_EMAIL']):
          print(return_details_to_display)
          orderID = return_details_to_display['order_id']
          for data in addresses:
            if data['OrderID'] == orderID:
              Address = data['Address']
              #print(Address)
          return render_template('home.html', tasks=queue, passed_value = return_details_to_display, tracking_id=tracking_id, queue_checker=queueChecker, address=Address,  user=current_user)
        else: 
            return render_template('home.html', tasks=queue,  user=current_user)
      
      else:
        flash('Account not complete. You do not have access to this page. Your are not subscribed.', category='error')
        return redirect('/account')
    else: 
      flash('Account not complete. You do not have access to this page. Your AmazonSellerCentral account is not linked.', category='error')
      return redirect('/account')
  else:
    flash('Your account is Restricted. Please contact us for more information.', category='error')
    return redirect('/account')

import time
@views.route('/refresh_returns_and_inventory')
@login_required
def refresh():
    count = 0
    #Get all the new return data with a call from amazonAPI.py
    #For debugging below>>
    all_return_data = get_all_Returns_data(current_user.refresh_token)
    inventory_data = checkInventory(current_user.refresh_token)
    addressData = get_addresses_from_GetOrders(current_user.refresh_token)
    # print("ADDRESS DATA:")
    # print(addressData)
    refresh_all_return_data_in_db(all_return_data, inventory_data, current_user.id)
    refresh_addresses_in_db(addressData, current_user.id)
    
    print('DEBUG MODE')
    return redirect('/')

    # try:
    #     print("Refreshing Returns and Inventory data:")
    #     print("Getting returns data: ")
    #     all_return_data = get_all_Returns_data(current_user.refresh_token)
    #     # print('all_return_data : ')
    #     # print(all_return_data)
    #     if (all_return_data != 'CANCELLED' and all_return_data!= 'FATAL'):
    #       inventory_data = checkInventory(current_user.refresh_token)
    #       if (inventory_data != 'CANCELLED' and all_return_data!= 'FATAL'):

    #         try:
    #           addressData = get_addresses_from_GetOrders(current_user.refresh_token)
    #           if addressData != 'EXCEPTION':
    #             try:
    #               refresh_all_return_data_in_db(all_return_data, inventory_data, current_user.id)
    #             except:
    #               return 'Could not refresh return data in database error views line 1databa32'
    #             refresh_addresses_in_db(addressData, current_user.id)
    #             flash(f'Successfully refreshed Returns and Inventory Data' ,category="success")
    #             return redirect('/')
    #           else:
    #             flash(f'Cannot get addressData. Received Exception' ,category='error')
    #         except:
    #           return 'There was a problem retrieving the addresses'
    #         return redirect('/')
    #       else:
    #          flash(f'The process checkInventory was terminated. Error message: {all_return_data}' ,category='error')
    #          return redirect('/')
    #     else:
    #       flash(f'The process get_all_Returns_data was terminated. Error message: {all_return_data}' ,category='error')
    #       return redirect('/')
        
    # except:
    #   return 'There was a problem refreshing your returns'



@views.route('/info_for_tracking_id', methods =[ 'POST', 'GET'])
@login_required
def get_info_on_track():
    trackingID = request.form['track']
    print(trackingID)
    new_trackingID = extract_tracking_id(trackingID)
    if new_trackingID:
        print(f"New Tracking ID: {new_trackingID}")
        trackingID = new_trackingID
  
    delete_tracking_id_to_search(current_user.id)
    add_tracking_id_to_search(trackingID, current_user.id)
    return redirect('/')
    
    #task_to_delete = TrackingIDS.query.get_or_404(id)
    #update the database to include data for the return

    try:
        #db.session.delete(task_to_delete)
        #db.session.commit()
        return redirect('/')
    except:
        return 'There was a problem getting the info for this return'

@views.route('/increase_inventory/<my_task_tracker_id>', methods =['POST', 'GET'])
@login_required
def increase_inventory(my_task_tracker_id):
  #take the tracking id's in the queue and increase inventory by the return order amount for each
  task = increase_inventory_task.delay(my_task_tracker_id, current_user.refresh_token, current_user.id)
  return redirect('/jobs')



@shared_task(bind=True, base=AbortableTask, retry_backoff=60, max_retries=3)
def increase_inventory_task(self, my_task_tracker_id, refresh_token, current_user_id):
  #Check if there are tasks with the same id and let the user know the pevious satuses of all of them
  try:
    task = Task.query.filter_by(id=self.request.id, user_id=current_user_id).all()
    print("CHECK OUT THESE TASKSKSKSKSKSKKSKSKSKSK:")
    print(task)
    if len(task) > 1:
      print ("BIIIIIIIIGGGGGG ERROR. MULTIPLE TASKS WITH SAME ID")
      return -1
    elif task:
      task = task[0]
    elif not task:
      task = Task(id=self.request.id, name='increase_inventory', description='Increasing Inventory...', time_created= datetime.now(), user_id=current_user_id, my_task_tracker=my_task_tracker_id )
      db.session.add(task)
      db.session.commit()
    Quantity_of_SKUS = checkInventory(refresh_token)
    result = increaseInventory(Quantity_of_SKUS, task.id, my_task_tracker_id, current_user_id, refresh_token)
    print("RESULT of increaseInventory():")
    print(type(result))
    print(result)
    # print(result[1])
    if result[0] == 'SUCCESS' :
        flash('Inventory Feed Submitted Successfully! It may take up to 2 hours to load on AmazonSellerCentral.', category='success')
    elif result[0] == None:
      # flash (f'error. The queue was probably empty: {result} ', category='error')
      print(f'error. The queue was probably empty: {result} ')
    else:
      # flash (f'error: {result} ', category='error')
      print(f'error: {result} ')
    # result = checkInventoryIncrease(Quantity_of_SKUS, result[1], current_user.refresh_token)
    # print(result)
    # if result == "Inventory Increased Successfully":
 
  except Exception as e:
    # Handle exceptions, log them, and roll back the transaction
    db.session.rollback()
    self.retry(exc=e)




@shared_task(bind=True, base=AbortableTask, retry_backoff=60, max_retries=3)
def print_numbers_task(self, seconds, id):
    # db.session.rollback()
    try:
      task = Task(id=self.request.id, name='print_numbers_task', description='Printing Numbers...', user_id=id)
      print('TASK:', task)
      db.session.add(task)
      db.session.commit()
    except OperationalError as e:
      db.session.rollback()
      db.session.close()
      # Log the error if needed
      print("DEBUG: A")
      self.retry(exc=e)
    except PendingRollbackError as e:
      # Rollback the session and retry the operation after a delay
        db.session.rollback()
        db.session.remove()
        print("DEBUG: ROLLBACK ERROR")
        self.retry(exc=e)
    except Exception as e:
        # Handle exceptions, log them, and roll back the transaction
        db.session.rollback()
        raise e
    finally:
        # Close the database connection after each task
        db.session.remove()
      
    print("Printing Numbers")
    print("Starting num task")
    for num in range(seconds):
        try:
          print(num)
          time.sleep(1)
          #Beginning of sequence to update progress
          self.update_state(state='PROGRESS',
            meta={'current': num, 'total': seconds, 'status': 'Printing'})
          progress = (num+1)/seconds * 100 #THIS CHANGES PER FUNCTION
          print("ID", self.request.id)
          task = Task.query.get(self.request.id)
          print(task)
          task.user.add_notification('task_progress', {'task_id': self.request.id, 'progress': progress})
          if progress >= 100:
              task.complete = True
              print('PROGRESS FINAL', progress)
          else:
            print('PROGRESS', progress)
            db.session.commit()
        except OperationalError as e:
          db.session.rollback()
          db.session.close()
          # Log the error if needed
          print("DEBUG: B")
          self.retry(exc=e)
        except Exception as e:
            # Handle exceptions, log them, and roll back the transaction
            db.session.rollback()
            raise e
        finally:
            # Close the database connection after each task
            db.session.remove()
        #End of sequence to update progress
        if(self.is_aborted()):
          print("Aborted")
          return "TASK STOPPED!"
    print("Task to print_numbers completed")
    return {'current': 100, 'total': 100, 'status': 'Task completed!', 'result': 42}


@views.route('/print_numbers', methods =['POST', 'GET'])
@login_required
def number_print():
  #take the tracking id's in the queue and increase inventory by the return order amount for each
  # current_user.launch_task('increase_inventory_function', 'Increasing Inventory...')
  #EVERY TIME YOU LAUNCH A TASK
  task = print_numbers_task.delay(40, current_user.id)
  print("TASK LAUNCHED: print_numbers_task - TASK_ID", task.id)
  return jsonify({}), 202, {'Location': url_for('views.taskstatus',
    task_id=task.id)}
  
  # print("PRINTING TASK:")
  # print(task)
  # print(task.id)
  # print(task.result)
  # print(task.status)
  # time.sleep(5)
  # print("PRINTING TASK2:")
  # print(task)
  # print(task.id)
  # print(task.result)
  # print(task.status)
  # rq_job = current_app.task_queue.enqueue('print_numbers', args=(5,))
  # task = Task(id=rq_job.get_id(), name='print_numbers', description='Printing Numbers...', user_id=current_user.id)
  # db.session.add(task)
  # db.session.commit()
  #return redirect('/')

@views.route('/status/<task_id>')
def taskstatus(task_id):
    task = print_numbers_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        # job did not start yet
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)


@views.route('/delete/<tracking>')
@login_required
def delete(tracking):
    delete_trackingID_from_queue_db(tracking, current_user.id)
    return redirect('/')
  
    try:
        delete_trackingID_from_queue_db(tracking, current_user.id)
        return redirect('/')
    except:
        return 'There was a problem deleting that task'




# @views.route('/add_trackingID', methods=['POST', 'GET'])
# @login_required
# def add_tracking_id():
#     tracking_id = request.form
#     print('test')
#     #print(tracking_id)
#     queue = load_queue_from_db(current_user.id) 
#     for track in queue:
#       if track['tracking'] == tracking_id:
#         print("Tracking ID is already in queue")
#         flash('Tracking ID is already in the queue.', category ='error')
#         return redirect ('/')
#     print("Successfully Added Tracking ID to Queue.")
#     # flash('Successfully Added Tracking ID to Queue.', category='success')
#     add_tracking_id_to_queue(tracking_id['added_track'], current_user.id)
#     return redirect('/')
    
#     try:
#       add_tracking_id_to_queue(tracking_id['added_track'], current_user.id)
#       return redirect('/')

#     except:
#       return 'There was a problem adding the Tracking ID to your queue'
@views.route('/add_to_queue_button', methods=['POST', 'GET'])
def add_to_queue():
  result=request.form
  # print(result)
  tracking_id = load_tracking_id_to_search(current_user.id)
  if tracking_id == None or tracking_id =='' :
    flash('Search is empty.', category='error')
    return redirect ('/')
  else: 
    tracking_id = load_tracking_id_to_search(current_user.id)
    return_data = load_current_return_to_display_from_db(current_user.id)
    quantity_of_return = return_data['return_quantity']
    sku = return_data['sku']
    queue = load_queue_from_db(current_user.id) 
    
    print(return_data)
    if return_data['order_id'] == 'Not Found':
      print('Cannot add unknown tracking id to queue')
      flash('Cannot add unknown tracking id to queue.', category ='error')
      return redirect('/')
    for track in queue:
        #print(track['tracking'])
        if track['tracking'] == tracking_id:
          print("Tracking ID is already in queue")
          flash("Tracking ID is already in queue", category = 'error')
          return redirect('/')
          
    print("Successfully Added Tracking ID to Queue.")
    add_tracking_id_to_queue(tracking_id, sku, quantity_of_return, current_user.id)
    # flash("Successfully Added Tracking ID to Queue.", category = 'success')
    return redirect('/')

@views.route('/search', methods=['POST','GET'])
@login_required
def search():
  delete_tracking_id_to_search(current_user.id)
  delete_current_return_to_display_from_db(current_user.id)
  tracking_id = request.form
  add_tracking_id_to_search(tracking_id)
#add_current_return_to_display_to_db(tracking_id)
  return redirect('/')
@views.route('/clearSearch')
@login_required
def clearSearch():
  time.sleep(10)
  print('test')
  time.sleep(10)
  time.sleep(10)
  time.sleep(10)
  delete_tracking_id_to_search(current_user.id)
  delete_current_return_to_display_from_db(current_user.id)
  return redirect('/')
@views.route('/clearQueue')
@login_required
def clearQueue():
  delete_whole_tracking_id_queue(current_user.id)
  return redirect('/')


@views.route('/account')
@login_required
def account():
  stripe.billing_portal.Configuration.create(
  business_profile={
    "headline": "AmazeSoftware partners with Stripe for simplified billing.",
  },
  features={"invoice_history": {"enabled": True}},
  metadata={'user_id': current_user.id}
)
  
  customer = Stripecustomer.query.filter_by(user_id=current_user.id).order_by(Stripecustomer.id.desc()).first() 
  if customer:
        subscription = stripe.Subscription.retrieve(customer.stripeSubscriptionId)
        product = stripe.Product.retrieve(subscription.plan.product)
        context = {
            "subscription": subscription,
            "product": product,
        }
    
  refresh_token = get_refresh_token(current_user.id)
  if (refresh_token and customer):
    return render_template('account.html', user=current_user, refresh_token=refresh_token, **context)
  elif customer:
    return render_template('account.html', user=current_user, **context)
  elif refresh_token:
    return render_template('account.html', user=current_user, refresh_token=refresh_token)

        
  return render_template('account.html', user=current_user)


@views.route('/admin')
@login_required
def admin():
  if(current_user.email== os.environ['ADMIN_EMAIL']): 
    users = load_users_from_db()
    deleted_users = load_deleted_users_from_db()
    stripe_customers = load_all_stripe_customers()
    #update subscription statuses in database to view by admin
    for user in users:
      customer = Stripecustomer.query.filter_by(user_id=user.id).order_by(Stripecustomer.id.desc()).first()
      subscription = None
      if customer:
        subscription = stripe.Subscription.retrieve(customer.stripeSubscriptionId)
      if subscription:
        user.status = subscription.status
        db.session.commit()
      else:
        user.status = None
        db.session.commit()
    
    #check for requested deletes
    requested_deletes ={}
    for user in users:
      if user.delete_request:
        requested_deletes[user.id] = 'requested delete'
    #Check for duplicate subscriptions
    duplicates={}
    for stripe_customer in stripe_customers:
      for check in stripe_customers:
        if stripe_customer.id != check.id and stripe_customer.user_id == check.user_id:
          duplicates[stripe_customer.user_id] = "duplicate"

    if duplicates:
      flash('There are users with duplicate subscriptions!', category='error')
    if requested_deletes:
      flash('There are users that requested to delete their accounts..', category='error')
    
    return render_template('admin.html', users=users,  user=current_user, deleted_users = deleted_users, requested_deletes = requested_deletes, duplicates = duplicates)
  else:
    flash('Access Denied.', category='error')
    return redirect(url_for('views.home'))

@views.route('/request_delete_user/<user>')
@login_required
def request_delete_user(user):
  add_request_to_delete_user(user)
  flash('Request to Delete Account Sent.', category='success')
  return redirect('/account')

    
@views.route('/delete_user/<user>')
@login_required
def delete_user(user):
  if(current_user.email==os.environ['ADMIN_EMAIL']): 
    delete_user_from_db(user, current_user.id)
    return redirect('/admin')
  else:
    flash('Access Denied.', category='error')
    return redirect(url_for('views.home'))

@views.route('/delete_deleted_user/<deleted_user>')
@login_required
def delete_deleted_user(deleted_user):
  if(current_user.email==os.environ['ADMIN_EMAIL']): 
    delete_deleted_user_from_db(deleted_user, current_user.id)
    return redirect('/admin')
  else:
    flash('Access Denied.', category='error')
    return redirect(url_for('views.home'))
@views.route('/clear_all_users')
@login_required
def clear_users():
  if(current_user.email==os.environ['ADMIN_EMAIL']): 
    clear_all_users_from_db(current_user.id)
    return redirect('/admin')
  else:
    flash('Access Denied.', category='error')
    return redirect(url_for('views.home'))
@views.route('/clear_all_deleted_users')
@login_required
def clear_deleted_users():
  if(current_user.email==os.environ['ADMIN_EMAIL']): 
    clear_all_deleted_users_from_db(current_user.id)
    return redirect('/admin')
  else:
    flash('Access Denied.', category='error')
    return redirect(url_for('views.home'))



@views.route('/download-queue-pdf')
def download_queue():
    response = download_queue_data(current_user.id)
    # buffer = BytesIO()
    # with open('website/static/files/queue.pdf', 'rb') as f:
    #     buffer.write(f.read())
    # buffer.seek(0)
    # os.remove('website/static/files/queue.pdf')
    # response = make_response(buffer.getvalue())
  
      # Set the appropriate headers for a PDF file download
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=queue.pdf'
  
    return response


@views.route('/download-inventoryUpdate-pdf')
def download_queue_and_inventory_change():
    response = download_queue_and_inventory_change_data(current_user.id, current_user.refresh_token)
    # buffer = BytesIO()
    # with open('website/static/files/InventoryUpdate.pdf', 'rb') as f:
    #     buffer.write(f.read())
    # buffer.seek(0)
    # os.remove('website/static/files/InventoryUpdate.pdf')
    # response = make_response(buffer.getvalue())
  
      # Set the appropriate headers for a PDF file download
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=InventoryUpdate.pdf'
  
    return response

@views.route('/download-inventoryChange-pdf')
def download_inventory_to_change_slim():
    response = download_inventory_change(current_user.id, current_user.refresh_token)
    # buffer = BytesIO()
    # with open('website/static/files/InventoryUpdate.pdf', 'rb') as f:
    #     buffer.write(f.read())
    # buffer.seek(0)
    # os.remove('website/static/files/InventoryUpdate.pdf')
    # response = make_response(buffer.getvalue())
  
      # Set the appropriate headers for a PDF file download
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=InventoryUpdate.pdf'
  
    return response
  

@views.route('/support', methods=['GET', 'POST'])
def support():
  if request.method == 'POST':
        suggestion = request.form.get('suggestion')
        add_suggestion(suggestion, current_user)
        flash('Suggestion sent. Thank you for your feedback!', category='success')
  return render_template('support.html', user=current_user)

@views.route('/jobs', methods=['GET', 'POST'])
@login_required
def jobs():
  # jobs_list = load_jobs_from_db(current_user.id)
  jobs_list = load_my_task_trackers_from_db(current_user.id)
  history = load_history_from_db_descending_order(current_user.id)

  return render_template('jobs.html', jobs = jobs_list, history=history, user=current_user)

@views.route('/create_job', methods=['GET', 'POST'])
@login_required
def create_job():
    try:
       # task = Task(id=self.request.id, name='print_numbers_task', description='Printing Numbers...', user_id=id)
      queue=load_queue_from_db(current_user.id)
      my_task_tracker = My_task_tracker(name='Increase Inventory' , description='Increasing Inventory...',   time_added_to_jobs = datetime.now(), status='Waiting', user_id=current_user.id)
      print('MY_TASK_TRACKER:', my_task_tracker)
      db.session.add(my_task_tracker)
      db.session.commit()
      add_queue_to_task_details(queue, my_task_tracker.id, current_user.id) 
      delete_whole_tracking_id_queue(current_user.id)
      message = f"Successfully created job with id: {my_task_tracker.id} .      It will execute at 12:00 am Est."
      flash(message, category='success')
    except OperationalError as e:
      db.session.rollback()
      db.session.close()
      # Log the error if needed
      print("DEBUG: A")
    except PendingRollbackError as e:
      # Rollback the session and retry the operation after a delay
        db.session.rollback()
        db.session.remove()
        print("DEBUG: ROLLBACK ERROR")
    except Exception as e:
        # Handle exceptions, log them, and roll back the transaction
        db.session.rollback()
        raise e
    finally:
        # Close the database connection after each task
        db.session.remove()
    return redirect(url_for('views.jobs'))

@views.route('/jobs/delete/<my_task>')
@login_required
def delete_job(my_task):
    delete_job_db(my_task, current_user.id)
    return redirect('/jobs')

@views.route('/jobs/info/<my_task>')
@login_required
def info_job(my_task):
    queue = get_info_job_from_db(my_task, current_user.id)
  
    return render_template('job_info.html', queue = queue, job_id=my_task, user=current_user)



# @views.route('/suggestion', methods=['GET', 'POST'])
# def suggestion():
    
  
  #   return send_file(buffer, mimetype='application/pdf', as_attachment=True,
  # attachment_filename='queue.pdf'
  #           )

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', debug=True)
@views.route('/notifications')
@login_required
def notifications():
    # since = request.args.get('since', 0.0, type=float)
    # notifications = current_user.notifications.filter(
    #     Notification.timestamp > since).order_by(Notification.timestamp.asc())
    notifications = current_user.notifications.filter().order_by(Notification.timestamp.asc())
    return jsonify([{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in notifications])

def extract_tracking_id(trackingID):
    # Define the patterns for the consecutive digits
    patterns = ['9400', '9205', '9407', '9303', '9208', '9202']

    # Check if the trackingID matches any of the patterns
    for pattern in patterns:
        match = re.search(pattern, trackingID)
        if match:
            start_index = match.start()
            new_trackingID = trackingID[start_index:]
            return new_trackingID

    return None  # Return None if no match is found




#for debugging. Remove later
@views.route('/rollback')
def rollback():

  task = rollback_db.delay()
  print("TASK LAUNCHED: rollback_db_task - TASK_ID", task.id)
  return redirect(url_for('views.home'))

@shared_task(bind=True, base=AbortableTask, retry_backoff=60, max_retries=3)
def rollback_db(self):
  db.session.rollback()
  db.session.close()
  print("Tried db rollback")
  return "Rolled back db"


@views.route('/load_task_details_from_db/<my_task_tracker_id>')
@login_required
def load_task_details(my_task_tracker_id):
  load_task_details_from_db(my_task_tracker_id, current_user.id)
  return redirect(url_for('views.home'))
























@views.route('/increase_inventory_web/<my_task_tracker_id>')
@login_required
def inventory_web_test(my_task_tracker_id):
   task = increase_inventory_task_web(my_task_tracker_id, current_user.refresh_token, current_user.id)
   return redirect('/jobs')






def increase_inventory_task_web(my_task_tracker_id, refresh_token, current_user_id):
  #Check if there are tasks with the same id and let the user know the pevious satuses of all of them
  try:
    Quantity_of_SKUS = checkInventory(refresh_token)
    result = increaseInventory_web2(Quantity_of_SKUS, my_task_tracker_id, current_user_id, refresh_token)
    print("RESULT of increaseInventory():")
    print(type(result))
    print(result)
    # print(result[1])
    if result[0] == 'SUCCESS' :
        flash('Inventory Feed Submitted Successfully! It may take up to 2 hours to load on AmazonSellerCentral.', category='success')
    elif result[0] == None:
      # flash (f'error. The queue was probably empty: {result} ', category='error')
      print(f'error. The queue was probably empty: {result} ')
    else:
      # flash (f'error: {result} ', category='error')
      print(f'error: {result} ')
    # result = checkInventoryIncrease(Quantity_of_SKUS, result[1], current_user.refresh_token)
    # print(result)
    # if result == "Inventory Increased Successfully":

  except Exception as e:
    # Handle exceptions, log them, and roll back the transaction
    
    print('ERROR', e)
    db.session.rollback()
    raise e








def increaseInventory_web1(Quantity_of_SKUS, my_task_tracker_id, user_id, refresh_token):

  result ={}
  credentials = dict(
    refresh_token=refresh_token,
    lwa_app_id=os.environ['LWA_CLIENT_ID'],
    lwa_client_secret=os.environ['LWA_CLIENT_SECRET'],
    aws_access_key=os.environ['AWS_ACCESS_KEY'],
    aws_secret_key=os.environ['AWS_SECRET_KEY'],  
    #role_arn="arn:aws:iam::108760843519:role/New_Role"
)
  #submitting feed to increase inventory   
  from io import BytesIO
  from sp_api.api import Feeds
  #from sp_api.auth import VendorCredentials
  import xml.etree.ElementTree as ET

  try:
    user = User.query.get(user_id)


    queue = load_task_details_from_db(my_task_tracker_id, user_id)
    queue_to_increase= {}
    is_duplicate = False
    for track in queue:
        track_sku_list = track['SKU'].split(', ')
        track_return_quantity_list = track['return_quantity'].split(', ') 
        i = 0
        for individual_sku in track_sku_list:  
          for sku in queue_to_increase.keys():
            if sku == individual_sku:
              is_duplicate = True
          if is_duplicate:
            queue_to_increase[individual_sku] = int(queue_to_increase[individual_sku]) + int(track_return_quantity_list[i])
            i+=1
          else:
            queue_to_increase[individual_sku]= int(track_return_quantity_list[i])
            i+=1
    print (queue_to_increase)
          #return queue_to_increase
    result[0] = None

  

    for sku in queue_to_increase.keys():
      # Initialize the Feeds API client
      feeds = Feeds(credentials=credentials)
      # Define the inventory update feed message
      message = {
              "MessageType": "Inventory",
              "MessageID": "1",
              "Inventory": {
                  "SKU": sku,
                  "Quantity": (int(Quantity_of_SKUS[sku])+int(queue_to_increase[sku])),
                  "FulfillmentCenterID": "DEFAULT"
              },
              "Override": "false"
          }

      # Create the XML structure
      root = ET.Element("AmazonEnvelope")
      root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
      root.set("xsi:noNamespaceSchemaLocation", "amzn-envelope.xsd")
      header = ET.SubElement(root, "Header")
      document_version = ET.SubElement(header, "DocumentVersion")
      document_version.text = "1.02"
      merchant_identifier = ET.SubElement(header, "MerchantIdentifier")
      merchant_identifier.text = "A2RSMNCJSAU6P5"  #Have to update this to make it generic

      message_type = ET.SubElement(root, "MessageType")
      message_type.text = message["MessageType"]

      message_element = ET.SubElement(root, "Message")
      message_id = ET.SubElement(message_element, "MessageID")
      message_id.text = message["MessageID"]

      inventory = ET.SubElement(message_element, "Inventory")
      inventory_data = message["Inventory"]
      seller_sku = ET.SubElement(inventory, "SKU")
      seller_sku.text = inventory_data["SKU"]
      fulfillment_center_id = ET.SubElement(inventory, "FulfillmentCenterID")
      fulfillment_center_id.text = inventory_data["FulfillmentCenterID"]

      # Choice between Available, Quantity, or Lookup
      quantity = ET.SubElement(inventory, "Quantity")
      quantity.text = str(inventory_data["Quantity"])

      restock_date = ET.SubElement(inventory, "RestockDate")
      restock_date.text = "2023-05-26"  # Replace with a valid date
      fulfillment_latency = ET.SubElement(inventory, "FulfillmentLatency")
      fulfillment_latency.text = "1"  # Replace with a valid integer
      switch_fulfillment_to = ET.SubElement(inventory, "SwitchFulfillmentTo")   #I think can leave this and following line out
      switch_fulfillment_to.text = "MFN"  # Replace with either "MFN" or "AFN  

      # Convert the XML structure to a string
      xml_string = ET.tostring(root, encoding="utf-8", method="xml")
      print(xml_string.decode("utf-8"))
      # Submit the feed
      feeds = Feeds(credentials=credentials)
      feed = BytesIO(xml_string)
      feed.seek(0)


      # Submit the feed
      try:
        document_response, create_feed_response= feeds.submit_feed('POST_INVENTORY_AVAILABILITY_DATA', feed, 'text/xml')
        #print("RETURNED DOCUMENT RESOPONSE")
        #print(document_response)
        #print ("RETURNED CREATE FEED RESPONSE")
        #print(create_feed_response)
        response = create_feed_response
        print("Feed submitted...")

        #Check the processing status
        #print(response)
        feed_id = response.payload.get('feedId')   
        #print (feed_id)

        print("Inventory Feed Processing Status")
        while True:
            feed_response = feeds.get_feed(feed_id)
            #print(feed_response)
            processing_status = feed_response.payload.get('processingStatus')
            print(processing_status) 
            if processing_status in ["DONE", "IN_QUEUE", "IN_PROGRESS"]:
                #print(f"Processing status: {processing_status}")
                if processing_status in ["DONE", "DONE_NO_DATA"]:
                    print(feed_response)
                    print("Feed processing completed.")

                    document_id = feed_response.payload.get("resultFeedDocumentId")
                    feed_response = Feeds(credentials=credentials).get_feed_document(document_id) #download=true
                    print(feed_response)
                    # return 'SUCCESS'
                    # delete_whole_tracking_id_queue(user_id)
                    result[0] = "SUCCESS"
                    result [1] = queue_to_increase        
  

                    break
            else:
                print("Feed processing encountered a fatal error.")

                result[0] = 'ERROR'
                break
            time.sleep(5)

      except Exception as e:
          print(f"Error submitting feed: {e}") 
          result[0] = e


    return result
  except:
    app.logger.error('Unhandled exception', exc_info=sys.exc_info())


def increaseInventory_web2(Quantity_of_SKUS, my_task_tracker_id, user_id, refresh_token):
  result ={}
  credentials = dict(
    refresh_token=refresh_token,
    lwa_app_id=os.environ['LWA_CLIENT_ID'],
    lwa_client_secret=os.environ['LWA_CLIENT_SECRET'],
    aws_access_key=os.environ['AWS_ACCESS_KEY'],
    aws_secret_key=os.environ['AWS_SECRET_KEY'],  
    #role_arn="arn:aws:iam::108760843519:role/New_Role"
)
  #submitting feed to increase inventory   
  from io import BytesIO
  from sp_api.api import Feeds
  #from sp_api.auth import VendorCredentials
  import xml.etree.ElementTree as ET
  print('Started IncreaseInventory_web2')
  queue = load_queue_from_db(user_id)
  print('QUEUE:', queue)
  queue_to_increase= {}
  is_duplicate = False
  for track in queue:
      track_sku_list = track['SKU'].split(', ')
      track_return_quantity_list = track['return_quantity'].split(', ') 
      i = 0
      for individual_sku in track_sku_list:  
        print("INDIVDUAL SKUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU:", individual_sku )
        for sku in queue_to_increase.keys():
          if sku == individual_sku:
            is_duplicate = True
        if is_duplicate:
          queue_to_increase[individual_sku] = int(queue_to_increase[individual_sku]) + int(track_return_quantity_list[i])
          i+=1
        else:
          queue_to_increase[individual_sku]= int(track_return_quantity_list[i])
          i+=1
  print (queue_to_increase)
        #return queue_to_increase
  result[0] = None
  for sku in queue_to_increase.keys():
    # Initialize the Feeds API client
    feeds = Feeds(credentials=credentials)
    # Define the inventory update feed message
    message = {
            "MessageType": "Inventory",
            "MessageID": "1",
            "Inventory": {
                "SKU": sku,
                "Quantity": (int(Quantity_of_SKUS[sku])+int(queue_to_increase[sku])),
                "FulfillmentCenterID": "DEFAULT"
            },
            "Override": "false"
        }

    # Create the XML structure
    root = ET.Element("AmazonEnvelope")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("xsi:noNamespaceSchemaLocation", "amzn-envelope.xsd")
    header = ET.SubElement(root, "Header")
    document_version = ET.SubElement(header, "DocumentVersion")
    document_version.text = "1.02"
    merchant_identifier = ET.SubElement(header, "MerchantIdentifier")
    merchant_identifier.text = "A2RSMNCJSAU6P5"

    message_type = ET.SubElement(root, "MessageType")
    message_type.text = message["MessageType"]

    message_element = ET.SubElement(root, "Message")
    message_id = ET.SubElement(message_element, "MessageID")
    message_id.text = message["MessageID"]

    inventory = ET.SubElement(message_element, "Inventory")
    inventory_data = message["Inventory"]
    seller_sku = ET.SubElement(inventory, "SKU")
    seller_sku.text = inventory_data["SKU"]
    fulfillment_center_id = ET.SubElement(inventory, "FulfillmentCenterID")
    fulfillment_center_id.text = inventory_data["FulfillmentCenterID"]

    # Choice between Available, Quantity, or Lookup
    quantity = ET.SubElement(inventory, "Quantity")
    quantity.text = str(inventory_data["Quantity"])

    restock_date = ET.SubElement(inventory, "RestockDate")
    restock_date.text = "2023-05-26"  # Replace with a valid date
    fulfillment_latency = ET.SubElement(inventory, "FulfillmentLatency")
    fulfillment_latency.text = "1"  # Replace with a valid integer
    switch_fulfillment_to = ET.SubElement(inventory, "SwitchFulfillmentTo")   #I think can leave this and following line out
    switch_fulfillment_to.text = "MFN"  # Replace with either "MFN" or "AFN  

    # Convert the XML structure to a string
    xml_string = ET.tostring(root, encoding="utf-8", method="xml")

    #debug
    print("XML STRING:")
    print(xml_string.decode("utf-8"))

    # Submit the feed
    feeds = Feeds(credentials=credentials)
    feed = BytesIO(xml_string)
    feed.seek(0)


    # Submit the feed
    try:
      document_response, create_feed_response= feeds.submit_feed('POST_INVENTORY_AVAILABILITY_DATA', feed, 'text/xml')
      #print("RETURNED DOCUMENT RESOPONSE")
      #print(document_response)
      #print ("RETURNED CREATE FEED RESPONSE")
      #print(create_feed_response)
      response = create_feed_response
      print("Feed submitted...")

      #Check the processing status
      #print(response)
      feed_id = response.payload.get('feedId')   
      #print (feed_id)

      print("Inventory Feed Processing Status")
      while True:
          feed_response = feeds.get_feed(feed_id)
          #print(feed_response)
          processing_status = feed_response.payload.get('processingStatus')
          print(processing_status) 
          if processing_status in ["DONE", "IN_QUEUE", "IN_PROGRESS"]:
              #print(f"Processing status: {processing_status}")
              if processing_status in ["DONE", "DONE_NO_DATA"]:
                  print(feed_response)
                  print("Feed processing completed.")

                  document_id = feed_response.payload.get("resultFeedDocumentId")
                  feed_response = Feeds(credentials=credentials).get_feed_document(document_id) #download=true
                  print(feed_response)
                  # return 'SUCCESS'
                  # delete_whole_tracking_id_queue(user_id)
                  result[0] = "SUCCESS"
                  result [1] = queue_to_increase
                  break
          else:
              print("Feed processing encountered a fatal error.")
              result[0] = 'ERROR'
              break
          time.sleep(5)

    except Exception as e:
        print(f"Error submitting feed: {e}") 
        result[0] = e

  return result
    

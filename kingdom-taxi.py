from flask import Flask, render_template, redirect, url_for, request, make_response
from email.message import EmailMessage
from smtplib import SMTP, SMTP_SSL
import sqlite3, json, ssl

# Constants for development use only.
email_server_label = 'hotmail'
recipient = 'captainmarley@hotmail.com'

# Send New Request Email to the driver with basic request information.
# Email has links to approve or deny the request which is processed by confirm_request().
def send_new_request_email(passengers, date, time, pass_email, driver_email):
    
    # Load email server configurations from the config.json file.
    for server in config['servers']:
        if server['label'] == email_server_label:
            email_config = server
            
    # Open the New Request Email HTML template and update it with the passed arguments.
    with app.open_resource('templates/new-request-email.html', mode = 'r') as file:
        body = file.read()
        body = body.format(p = passengers, d = date, t = time, e = pass_email)
        
    # Build the email message.
    message = EmailMessage()
    message["Subject"] = "New Ride Request"
    message["From"] = email_config['user']
    message["To"] = driver_email #'3525527139@mymetropcs.com'
    message.set_content('Enable HTML messages to see this content')
    message.add_alternative(body, subtype='html')
    
    # Connect to the email server and send the email message.
    with SMTP(email_config['host'], email_config['port']) as email_server:
        email_server.starttls(context = ssl.create_default_context())
        email_server.login(email_config['user'], email_config['password'])
        email_server.send_message(message)

# Sort by date, time and driver in that order.
def sort_key(obj):
    return obj[1]+obj[2]+obj[0]

# Create Flask app instance.
# Remainder of the program is Flask
app = Flask(__name__)

with app.open_resource('static/config.json') as file:
    config = json.load(file)
    
app.config['SECRET_KEY'] = config['secret_key']

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/add-ride', methods = ['POST'])
def add_ride():

    # Build a tuple that represents the new record.
    driver = request.form['driver']
    date = request.form['date']
    time = request.form['time']
    seats = request.form['seats']
    record = (driver, date, time, seats, 0)
    
    # Update the ride table with the new record.
    con = sqlite3.connect('kingdomtaxi.db')
    try:
        con.execute('INSERT INTO ride VALUES (?, ?, ?, ?, ?)', record)
        con.commit()
        
    except sqlite3.Warning as warning:
        print(warning)
        
    except sqlite3.Error as error:
        print("Type: '{}' Message: '{}'".format(type(error), error))
        con.rollback()
        
    con.close()
    
    # Get existing rides for driver
    # Redisplay the admin page with driver rides
    con = sqlite3.connect('kingdomtaxi.db')
    cur = con.execute('SELECT * FROM ride WHERE driver = ?', (driver,))
    
    driver_rides = []
    for ride in cur:
        driver_rides.append(ride)
        
    con.close()
    
    driver_rides.sort(key=sort_key)
    return render_template('admin.html', data = driver_rides)

@app.route('/all-rides', methods = ['POST'])
def all_rides():
    
    # Get existing rides and reload admin page
    con = sqlite3.connect('kingdomtaxi.db')
    cur = con.execute('SELECT * FROM ride')

    rides = []
    for ride in cur:
        rides.append(ride)

    con.close()

    rides.sort(key=sort_key)
    return render_template('admin.html', data = rides)

@app.route('/confirm-request/<email>/<answer>')
def confirm_request(email, answer):
    print(email, answer)
    return render_template('index.html')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/rides', methods = ['POST'])
def rides():
    
    send_new_request_email('2', '2022-08-09', '11:00', recipient, recipient)
    
    resp = make_response(render_template('rides.html'))
    
    resp.set_cookie('type', request.form['type'])
    resp.set_cookie('passengers', request.form['passengers'])
    resp.set_cookie('arrival', request.form['arrival'])
    resp.set_cookie('departure', request.form['departure'])
    
    return resp

@app.route('/arrival')
def arrival():
    arrival = request.form
    return render_template('arrival.html', arrival = arrival)

if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 80, debug = True)
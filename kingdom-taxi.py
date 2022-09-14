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

# Sort rides by date, time and driver in that order.
def sort_rides(obj):
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
    print(type(date))
    print(type(time))
    
    # Update the ride table with the new record.
    con = sqlite3.connect('kingdom-taxi.db')
    try:
        con.execute('INSERT INTO rides VALUES (?, ?, ?, ?, ?)', record)
        con.commit()
        
    except sqlite3.Warning as warning:
        print(warning)
        
    except sqlite3.Error as error:
        print("Type: '{}' Message: '{}'".format(type(error), error))
        con.rollback()
        
    con.close()
    
    # Get existing rides for driver
    # Redisplay the admin page with driver rides
    con = sqlite3.connect('kingdom-taxi.db')
    cur = con.execute('SELECT * FROM rides WHERE driver = ?', (driver,))
    
    driver_rides = []
    for ride in cur:
        driver_rides.append(ride)
        
    con.close()
    
    driver_rides.sort(key = sort_rides)
    return render_template('admin.html', data = driver_rides)

@app.route('/all-rides', methods = ['POST'])
def all_rides():
    
    # Get existing rides and reload admin page
    con = sqlite3.connect('kingdom-taxi.db')
    cur = con.execute('SELECT * FROM rides')

    rides = []
    for ride in cur:
        rides.append(ride)

    con.close()

    rides.sort(key = sort_rides)
    return render_template('admin.html', data = rides)

@app.route('/confirm-request/<email>/<answer>')
def confirm_request(email, answer):
    print(email, answer)
    return render_template('index.html')

@app.route('/')
def index():

    # Clear cookies for slected rides on subsequent screens.
    res = make_response(render_template('index.html'))
    res.set_cookie('ride1')
    res.set_cookie('ride2')

    return res

@app.route('/list-rides', methods = ['POST'])
def list_rides():
    
    # If we are coming from index, data is posted from the form.
    #   Ride1 needs to be selected.
    # Else the data is already saved in the cookies.
    #   Ride2 needs to be selected.
    if request.method == 'POST':
        date = request.form.get('date1')
        travelers = request.form.get('travelers')
    else:
        date = request.cookies.get('date2')
        travelers = request.cookies.get('travelers')
    query_args = (date, int(travelers))
    
    # Select rides from the database.
    con = sqlite3.connect('kingdom-taxi.db')
    cur = con.execute('\
    SELECT driver, date, time, seats - passengers \
    FROM rides \
    WHERE date = ? and (seats - passengers) >= ?', query_args)
    
    # Save the matching rides into a list.
    matching_rides = []
    for ride in cur:
        matching_rides.append(ride)
    matching_rides.sort(key = sort_rides)
    con.close()
    
    # Send the matching rides to the screen.
    # Set the basic information cookies if coming from index.
    res = make_response(render_template('list-rides.html', data = matching_rides))
    if request.method == 'POST':
        res.set_cookie('type', request.form.get('type'))
        res.set_cookie('date1', request.form.get('date1'))
        res.set_cookie('date2', request.form.get('date2'))
        res.set_cookie('travelers', request.form.get('travelers'))
    
    return res

@app.route('/select-ride')
def select_ride():
    type = request.cookies.get('type')
    ride1 = request.cookies.get('ride1','')
    selected_ride = request.args.get('ride')

    # If this is the first ride the user is selecting...
    if ride1 == '':
    
        # If this is a one way trip, the user can move on to the next screen.
        if type == 1:
            res = make_response(render_template('index.html'))
            res.set_cookie('ride1', selected_ride)
    
        # If this is a two way trip, the user needs to select the next ride.
        else:
            res = redirect(url_for('list_rides'))
            res.set_cookie('ride1', selected_ride)
    
    # This is the second ride selected in a two way trip,
    else:
        res = make_response(render_template('index.html'))
        res.set_cookie('ride2', selected_ride)
        
    return res

if __name__ == '__main__':
    app.run(debug = True, port = 5000)
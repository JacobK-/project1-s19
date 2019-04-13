#!/usr/bin/env python2.7

"""
Columbia W4111 Intro to databases
Example webserver

To run locally

        python server.py

Go to http://localhost:8111 in your browser


A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
import json
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect
from flask import Response, session

with open('credentials.json') as data_file:
    creds = json.load(data_file)
DB_USER = creds['db_user']
DB_PASSWORD = creds['db_pass']
DB_SERVER = creds['db_server']

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.secret_key = creds['secret_key']

# XXX: The Database URI should be in the format of: 
#   postgresql://USER:PASSWORD@<IP_OF_POSTGRE_SQL_SERVER>/<DB_NAME>
#
# For example, if you had username ewu2493, password foobar,
#    then the following line would be:
#        DATABASEURI =
#             "postgresql://ewu2493:foobar@<IP_OF_POSTGRE_SQL_SERVER>/postgres"
# For your convenience, we already set it to the class database

# Use the DB credentials you received by e-mail

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"


#
# Creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)


# Here we create a test table and insert some values in it
engine.execute("""DROP TABLE IF EXISTS test;""")
engine.execute("""CREATE TABLE IF NOT EXISTS test (
    id serial,
    name text
);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'),
    ('alan turing'), ('ada lovelace');""")


@app.before_request
def before_request():
    """
    This function is run at the beginning of every web request
    (every time you enter an address in the web browser).
    Used to setup a database connection that can be used throughout the request

    The variable g is globally accessible
    """
    try:
        g.conn = engine.connect()
    except:
        print("uh oh, problem connecting to database")
        import traceback
        traceback.print_exc()
        g.conn = None


@app.teardown_request
def teardown_request(exception):
    """
    At the end of the web request, ensures the database connection is closed.
    If you don't the database could run out of memory!
    """
    try:
        g.conn.close()
    except Exception as e:
        pass


#
# @app.route is a decorator around index() that means:
# run index() whenever a user tries to access the "/" path using a GET request
#
# If you wanted the user to go to e.g., localhost:8111/foobar/
#   with POST or GET then you could use
#     @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators:
#   http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/')
def index():
    """
    request is a special object that Flask provides to access web request
      information:

    request.method:     "GET" or "POST"
    request.form:         if the browser submitted a form,
        this contains the data in the form
    request.args:         dictionary of URL arguments e.g., {a:1, b:2} for
        http://localhost?a=1&b=2

    See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
    """
    if ('uid' not in session or session['uid'] is None):
        return redirect('/login')
    # DEBUG: this is debugging code to see what request looks like
    print(request.args)

    #
    # example of a database query
    #
    if ('home_name' not in session):
        cmd = '''SELECT name FROM LOCATION where lid=:user_home'''
        res = g.conn.execute(text(cmd), user_home=session['home'])
        session['home_name'] = res.fetchone()[0]
        res.close()

    # Get friends
    cmd = '''SELECT * FROM USERS JOIN USER_FRIENDS on USER_FRIENDS.uid_2 =
        USERS.uid  WHERE USER_FRIENDS.uid=1'''
    res = g.conn.execute(text(cmd), uid=session['uid'])
    data = list()
    for row in res:
        data.append([row['name']])
    res.close()
    print(data)

    #
    # Flask uses Jinja templates, which is an extension to HTML where you can
    # pass data to a template and dynamically generate HTML based on the data
    # (you can think of it as simple PHP)
    # documentation:
    #     https://realpython.com/blog/python/primer-on-jinja-templating/
    #
    # You can see an example template in templates/index.html
    #
    # context are the variables that are passed to the template.
    # for example, "data" key in the context variable defined below will be 
    # accessible as a variable in index.html:
    #
    #         # will print: [u'grace hopper', u'alan turing', u'ada lovelace']
    #         <div>{{data}}</div>
    #         
    #         # creates a <div> tag for each element in data
    #         # will print: 
    #         #
    #         #     <div>grace hopper</div>
    #         #     <div>alan turing</div>
    #         #     <div>ada lovelace</div>
    #         #
    #         {% for n in data %}
    #         <div>{{n}}</div>
    #         {% endfor %}
    #
    context = dict(data=data)

    #
    # render_template looks in the templates/ folder for files.
    # for example, the below file reads template/index.html
    #
    return render_template("index.html", **context)

#
# This is an example of a different path.    You can see it at
#
#         localhost:8111/another
#
# notice that the functio name is another() rather than index()
# the functions for each app.route needs to have different names
#


@app.route('/another')
def another():
    return render_template("anotherfile.html")


# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
    name = request.form['name']
    print(name)
    cmd = 'INSERT INTO test(name) VALUES (:name1), (:name2)'
    g.conn.execute(text(cmd), name1=name, name2=name)
    return redirect('/')


# Example of adding new data to the database
@app.route('/loginreq', methods=['POST'])
def loginreq():
    username = request.form['username']
    password = request.form['password']
    cmd = '''SELECT COUNT(*), MIN(uid), MIN(name), MIN(profile_picture),
        MIN(home) FROM USERS where email=:username and password=:password'''
    res = g.conn.execute(text(cmd), username=username,
                         password=password).fetchone()

    if(res[0] == 1):
        session['uid'] = res[1]
        session['name'] = res[2]
        session['profile_picture'] = res[3]
        session['home'] = res[4]
        return redirect('/')
    return redirect('/login')


@app.route('/login')
def login():
    return render_template("login.html")
    # abort(401)
    # this_is_never_executed()


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == "__main__":
    import click

    @click.command()
    @click.option('--debug', is_flag=True)
    @click.option('--threaded', is_flag=True)
    @click.argument('HOST', default='0.0.0.0')
    @click.argument('PORT', default=8111, type=int)
    def run(debug, threaded, host, port):
        """
        This function handles command line parameters.
        Run the server using

                python server.py

        Show the help text using

                python server.py --help

        """

        HOST, PORT = host, port
        print("running on %s:%d" % (HOST, PORT))
        app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

    run()

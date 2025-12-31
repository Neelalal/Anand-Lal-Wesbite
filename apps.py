# -*- coding: utf-8 -*-
"""
Created on Wed Dec 13 18:29:49 2023

@author: neell
"""
from flask import Flask, render_template
from gevent.pywsgi import WSGIServer

app = Flask(__name__)

# Define routes for your website
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/portfolio')
def portfolio():
    return render_template('portfolio.html')

if __name__ == '__main__':
    app.run(debug=True)
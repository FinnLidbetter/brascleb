
from flask import render_template
from flask_restful import Resource


class IndexView(Resource):

    @staticmethod
    def get():
        return render_template('index.html')

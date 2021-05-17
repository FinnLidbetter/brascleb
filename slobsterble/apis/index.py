
from flask import render_template, Response
from flask_restful import Resource


class IndexView(Resource):

    @staticmethod
    def get():
        return Response(render_template('index.html'), status=200)

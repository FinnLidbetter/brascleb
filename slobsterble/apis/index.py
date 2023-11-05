from flask import Response, render_template
from flask_restful import Resource


class IndexView(Resource):
    @staticmethod
    def get():
        return Response(render_template("index.html"), status=200)

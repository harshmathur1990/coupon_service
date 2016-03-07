from gevent import monkey
monkey.patch_all()
from gevent.wsgi import WSGIServer
from flask import Flask
# from users import user_routes
# from posts import post_routes

app = Flask(__name__)
# app.register_blueprint(user_routes)
# app.register_blueprint(post_routes)


if __name__ == "__main__":
    app.debug = True
    http_server = WSGIServer(('', 8000), app)
    http_server.serve_forever()
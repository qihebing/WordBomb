from app import app
from app.routes.words import bp as words_bp

app.register_blueprint(words_bp)

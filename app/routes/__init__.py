from app import app
from app.routes.words import bp as words_bp
from app.routes.games import bp as games_bp

app.register_blueprint(words_bp)
app.register_blueprint(games_bp)

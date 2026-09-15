from app import app
from app.routes.main import bp as main_bp
from app.routes.validation import bp as validation_bp
from app.routes.games import bp as games_bp

app.register_blueprint(main_bp)
app.register_blueprint(validation_bp)
app.register_blueprint(games_bp)

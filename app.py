from flask import Flask, jsonify
from flasgger import Swagger
from config import Config
from database.connections import db
from swagger_config import swagger_config, swagger_template
from utils.logger import logger

from routes.auth_routes import auth_bp
from routes.complaint_routes import complaint_bp
from routes.user_routes import user_bp
from routes.escalation_routes import escalation_bp
from routes.upload_routes import upload_bp
from routes.notification_routes import notification_bp

app = Flask(__name__)
app.config.from_object(Config)

swagger = Swagger(app, config=swagger_config, template=swagger_template)

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(complaint_bp, url_prefix='/api')
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(escalation_bp, url_prefix='/api')
app.register_blueprint(upload_bp, url_prefix='/api')
app.register_blueprint(notification_bp, url_prefix='/api')

logger.info("All blueprints registered successfully")


@app.route('/health', methods=['GET'])
def health_check():
    """
    Check server and database health status.
    ---
    tags:
      - Health
    responses:
      200:
        description: Server is healthy
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            message:
              type: string
              example: Server is running
            database:
              type: string
              example: connected
      500:
        description: Database connection failed
    """
    if db is not None:
        logger.info("Health check passed")
        return jsonify({
            "status": "success",
            "message": "Server is running",
            "database": "connected"
        }), 200
    logger.error("Health check failed — DB not connected")
    return jsonify({
        "status": "fail",
        "message": "Database not connected"
    }), 500


@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 - Route not found")
    return jsonify({"status": "fail", "error": "Route not found"}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    logger.warning(f"405 - Method not allowed")
    return jsonify({"status": "fail", "error": "Method not allowed"}), 405


@app.errorhandler(413)
def file_too_large(error):
    logger.warning("413 - File too large")
    return jsonify({
        "status": "fail",
        "error": "File too large. Maximum size is 5MB"
    }), 413


@app.errorhandler(500)
def server_error(error):
    logger.error(f"500 - Internal server error: {error}")
    return jsonify({
        "status": "fail",
        "error": "Internal server error"
    }), 500


if __name__ == '__main__':
    logger.info("Starting Complaint Management Platform...")
    logger.info("Swagger UI available at: http://127.0.0.1:5000/docs")
    app.run(debug=True)
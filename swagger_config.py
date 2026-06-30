swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs",
    "title": "Complaint Management Platform"
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Complaint Management Platform API",
        "description": """
    ## Welcome to the Complaint Management Platform API

    ### How to Authenticate:
    1. Use **POST /api/auth/register** to create an account
    2. Use **POST /api/auth/login** to get your JWT token
    3. Click the **Authorize** button (🔒) at the top right
    4. Enter your token in this exact format: `Bearer <your_token_here>`"""
    },
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header using the Bearer scheme. Example: \"Bearer {token}\""
        }
    }
}
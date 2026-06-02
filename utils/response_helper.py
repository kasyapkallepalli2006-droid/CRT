from flask import jsonify

def success_response(message, data=None, status_code=200):
    """
    Builds a consistent success response.

    Example output:
    {
        "status": "success",
        "message": "Complaint created",
        "data": { ... }
    }
    """
    response = {
        "status": "success",
        "message": message
    }

    # Only include data key if data was provided
    if data is not None:
        response["data"] = data

    return jsonify(response), status_code


def error_response(message, status_code=400):
    """
    Builds a consistent error response.

    Example output:
    {
        "status": "fail",
        "error": "Title is required"
    }
    """
    return jsonify({
        "status": "fail",
        "error": message
    }), status_code
from flask import Blueprint, jsonify
from middleware.auth_middleware import token_required, admin_required
from database.connections import db
import datetime

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/summary', methods=['GET'])
@token_required
@admin_required
def get_summary(current_user):
    """
    Get platform-wide complaint and user summary stats. Admin only.
    ---
    tags:
      - Analytics
    security:
      - Bearer: []
    responses:
      200:
        description: Summary metrics fetched successfully
      403:
        description: Admin access required
    """
    try:
        total = db.complaints.count_documents({})
        active = db.complaints.count_documents({"status": {"$in": ["Pending", "Assigned", "In Progress", "Escalated"]}})
        resolved = db.complaints.count_documents({"status": "Resolved"})
        closed = db.complaints.count_documents({"status": "Closed"})
        escalated = db.complaints.count_documents({"status": "Escalated"})

        total_users = db.users.count_documents({"role": "user"})
        total_admins = db.users.count_documents({"role": "admin"})

        resolution_rate = round(((resolved + closed) / total) * 100, 1) if total > 0 else 0.0
        escalation_rate = round((escalated / total) * 100, 1) if total > 0 else 0.0

        return jsonify({
            "status": "success",
            "data": {
                "complaints": {
                    "total": total,
                    "active": active,
                    "resolved": resolved,
                    "closed": closed,
                    "escalated": escalated
                },
                "users": {
                    "total_users": total_users,
                    "total_admins": total_admins
                },
                "rates": {
                    "resolution_rate_percent": resolution_rate,
                    "escalation_rate_percent": escalation_rate
                }
            }
        }), 200
    except Exception as e:
        return jsonify({"status": "fail", "error": str(e)}), 500


@analytics_bp.route('/status', methods=['GET'])
@token_required
@admin_required
def get_status_distribution(current_user):
    """
    Get complaint counts and percentages grouped by status. Admin only.
    ---
    tags:
      - Analytics
    security:
      - Bearer: []
    responses:
      200:
        description: Status distribution fetched successfully
    """
    try:
        total = db.complaints.count_documents({})
        statuses = ['Pending', 'Assigned', 'In Progress', 'Escalated', 'Resolved', 'Closed']
        data = []
        for s in statuses:
            count = db.complaints.count_documents({"status": s})
            percentage = round((count / total) * 100, 1) if total > 0 else 0.0
            data.append({
                "status": s,
                "count": count,
                "percentage": percentage
            })
        return jsonify({
            "status": "success",
            "data": {
                "data": data
            }
        }), 200
    except Exception as e:
        return jsonify({"status": "fail", "error": str(e)}), 500


@analytics_bp.route('/category', methods=['GET'])
@token_required
@admin_required
def get_category_breakdown(current_user):
    """
    Get total and resolved complaints grouped by category. Admin only.
    ---
    tags:
      - Analytics
    security:
      - Bearer: []
    responses:
      200:
        description: Category breakdown fetched successfully
    """
    try:
        categories = ['Infrastructure', 'Electricity', 'Water', 'Internet', 'Transport', 'Service Issue', 'Others']
        data = []
        for cat in categories:
            total_cat = db.complaints.count_documents({"category": cat})
            resolved_cat = db.complaints.count_documents({"category": cat, "status": {"$in": ["Resolved", "Closed"]}})
            data.append({
                "category": cat,
                "total": total_cat,
                "resolved": resolved_cat
            })
        return jsonify({
            "status": "success",
            "data": {
                "data": data
            }
        }), 200
    except Exception as e:
        return jsonify({"status": "fail", "error": str(e)}), 500


@analytics_bp.route('/trends', methods=['GET'])
@token_required
@admin_required
def get_trends(current_user):
    """
    Get monthly trends for the current year. Admin only.
    ---
    tags:
      - Analytics
    security:
      - Bearer: []
    responses:
      200:
        description: Monthly trends fetched successfully
    """
    try:
        year = datetime.datetime.utcnow().year
        start_date = datetime.datetime(year, 1, 1)
        end_date = datetime.datetime(year + 1, 1, 1)

        pipeline = [
            {"$match": {
                "created_at": {"$gte": start_date, "$lt": end_date}
            }},
            {"$project": {
                "month": {"$month": "$created_at"},
                "status": "$status"
            }},
            {"$group": {
                "_id": "$month",
                "total": {"$sum": 1},
                "resolved": {"$sum": {"$cond": [{"$in": ["$status", ["Resolved", "Closed"]]}, 1, 0]}},
                "escalated": {"$sum": {"$cond": [{"$eq": ["$status", "Escalated"]}, 1, 0]}}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        results = list(db.complaints.aggregate(pipeline))
        results_map = {r['_id']: r for r in results}

        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        monthly_trends = []

        for m in range(1, 13):
            name = month_names[m - 1]
            if m in results_map:
                monthly_trends.append({
                    "month": name,
                    "total": results_map[m]['total'],
                    "resolved": results_map[m]['resolved'],
                    "escalated": results_map[m]['escalated']
                })
            else:
                monthly_trends.append({
                    "month": name,
                    "total": 0,
                    "resolved": 0,
                    "escalated": 0
                })

        return jsonify({
            "status": "success",
            "data": {
                "year": year,
                "monthly_trends": monthly_trends
            }
        }), 200
    except Exception as e:
        return jsonify({"status": "fail", "error": str(e)}), 500


@analytics_bp.route('/top-users', methods=['GET'])
@token_required
@admin_required
def get_top_users(current_user):
    """
    Get top 3 users with the highest count of submitted complaints. Admin only.
    ---
    tags:
      - Analytics
    security:
      - Bearer: []
    responses:
      200:
        description: Top complainants fetched successfully
    """
    try:
        pipeline = [
            {"$group": {
                "_id": "$user_id",
                "total_complaints": {"$sum": 1},
                "resolved": {"$sum": {"$cond": [{"$in": ["$status", ["Resolved", "Closed"]]}, 1, 0]}}
            }},
            {"$sort": {"total_complaints": -1}},
            {"$limit": 3},
            {"$lookup": {
                "from": "users",
                "localField": "_id",
                "foreignField": "_id",
                "as": "user_info"
            }},
            {"$unwind": "$user_info"},
            {"$project": {
                "name": "$user_info.name",
                "email": "$user_info.email",
                "total_complaints": 1,
                "resolved": 1
            }}
        ]
        top_complainants = list(db.complaints.aggregate(pipeline))
        for t in top_complainants:
            t['id'] = str(t['_id'])
            del t['_id']

        return jsonify({
            "status": "success",
            "data": {
                "top_complainants": top_complainants
            }
        }), 200
    except Exception as e:
        return jsonify({"status": "fail", "error": str(e)}), 500

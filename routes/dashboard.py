"""
routes/dashboard.py
--------------------
Landing dashboard (stats + quick actions) and the deeper Analytics page
(charts for risk distribution, query categories, customer segments).
"""

from flask import Blueprint, render_template, session, redirect, url_for
from sqlalchemy import func

from database.database import db
from database.models import User, Conversation, Message, BusinessPlan, Prediction, BusinessProfile
from routes.auth import login_required
from ml.segmentation import get_segment_summary

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    """Public landing page."""
    if session.get("user_id"):
        return redirect(url_for("dashboard.dashboard_home"))
    return render_template("index.html")


@dashboard_bp.route("/dashboard")
@login_required
def dashboard_home():
    user_id = session["user_id"]

    total_queries = Message.query.filter_by(sender="user").join(Conversation).filter(
        Conversation.user_id == user_id
    ).count()
    total_plans = BusinessPlan.query.filter_by(user_id=user_id).count()
    total_businesses = BusinessProfile.query.filter_by(user_id=user_id).count()
    raw_predictions = Prediction.query.filter_by(user_id=user_id).count()
    total_predictions = raw_predictions + total_businesses

    low_risk = Prediction.query.filter_by(user_id=user_id, predicted_risk="Low Risk").count() + \
               BusinessProfile.query.filter_by(user_id=user_id, predicted_risk="Low Risk").count()
    medium_risk = Prediction.query.filter_by(user_id=user_id, predicted_risk="Medium Risk").count() + \
                  BusinessProfile.query.filter_by(user_id=user_id, predicted_risk="Medium Risk").count()
    high_risk = Prediction.query.filter_by(user_id=user_id, predicted_risk="High Risk").count() + \
                BusinessProfile.query.filter_by(user_id=user_id, predicted_risk="High Risk").count()

    recent_conversations = (
        Conversation.query.filter_by(user_id=user_id)
        .order_by(Conversation.created_at.desc())
        .limit(5)
        .all()
    )

    recent_businesses = (
        BusinessProfile.query.filter_by(user_id=user_id)
        .order_by(BusinessProfile.created_at.desc())
        .limit(5)
        .all()
    )

    stats = {
        "total_queries": total_queries,
        "total_plans": total_plans,
        "total_businesses": total_businesses,
        "total_predictions": total_predictions,
        "low_risk": low_risk,
        "medium_risk": medium_risk,
        "high_risk": high_risk,
    }

    return render_template(
        "dashboard.html",
        stats=stats,
        recent_conversations=recent_conversations,
        recent_businesses=recent_businesses
    )


@dashboard_bp.route("/analytics")
@login_required
def analytics():
    user_id = session["user_id"]

    # Risk distribution (this user's predictions)
    risk_counts = {
        "Low Risk": Prediction.query.filter_by(user_id=user_id, predicted_risk="Low Risk").count(),
        "Medium Risk": Prediction.query.filter_by(user_id=user_id, predicted_risk="Medium Risk").count(),
        "High Risk": Prediction.query.filter_by(user_id=user_id, predicted_risk="High Risk").count(),
    }

    # Query category distribution (this user's chat messages)
    category_rows = (
        db.session.query(Message.category, func.count(Message.id))
        .join(Conversation)
        .filter(Conversation.user_id == user_id, Message.sender == "user")
        .group_by(Message.category)
        .all()
    )
    category_counts = {cat or "Uncategorized": count for cat, count in category_rows}

    # Platform-wide totals (for context)
    platform_totals = {
        "total_users": User.query.count(),
        "total_predictions": Prediction.query.count(),
        "total_business_plans": BusinessPlan.query.count(),
    }

    # Customer segmentation (K-Means) — trained once, cached to disk
    try:
        segmentation_summary = get_segment_summary()
    except Exception:
        segmentation_summary = {"segments": {}, "cluster_stats": []}

    return render_template(
        "analytics.html",
        risk_counts=risk_counts,
        category_counts=category_counts,
        platform_totals=platform_totals,
        segmentation_summary=segmentation_summary,
    )

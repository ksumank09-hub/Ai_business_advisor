"""
routes/business.py
-------------------
Business Plan Generator and Market Analysis features.
Both use the LLM when available, and fall back to structured Demo Mode
templates when no LLM API key is configured (or if the live call fails).
"""

from flask import Blueprint, render_template, request, session, flash

from database.database import db
from database.models import BusinessPlan
from routes.auth import login_required
from ai.llm import generate_raw_completion
from ai.prompts import demo_business_plan_template, demo_market_analysis_template
from config import Config

business_bp = Blueprint("business", __name__)


@business_bp.route("/business-plan", methods=["GET", "POST"])
@login_required
def business_plan():
    generated_plan = None
    form_data = {}

    if request.method == "POST":
        business_name = request.form.get("business_name", "").strip()
        business_type = request.form.get("business_type", "").strip()
        location = request.form.get("location", "").strip()
        budget = request.form.get("budget", "").strip()
        target_customers = request.form.get("target_customers", "").strip()
        product = request.form.get("product", "").strip()
        goals = request.form.get("goals", "").strip()

        form_data = {
            "business_name": business_name, "business_type": business_type,
            "location": location, "budget": budget,
            "target_customers": target_customers, "product": product, "goals": goals,
        }

        if not business_name or not business_type:
            flash("Business name and business type are required.", "danger")
            return render_template("business_plan.html", form_data=form_data, generated_plan=None)
            
        if budget:
            try:
                b_val = float(budget)
                if b_val <= 0:
                    flash("Invalid budget.", "danger")
                    return render_template("business_plan.html", form_data=form_data, generated_plan=None)
            except ValueError:
                flash("Invalid budget.", "danger")
                return render_template("business_plan.html", form_data=form_data, generated_plan=None)

        # Try live LLM first (if configured), else Demo Mode template
        if not Config.DEMO_MODE:
            prompt = (
                "Generate a structured business plan with sections: Executive Summary, "
                "Business Description, Target Market, Customer Segments, Competitor Analysis, "
                "Marketing Strategy, Operations Plan, Financial Overview, Risk Analysis, "
                f"Growth Strategy.\n\nDetails:\n{form_data}"
            )
            llm_result = generate_raw_completion(prompt)
            generated_plan = llm_result["response"]

        if not generated_plan:  # demo mode OR live call failed
            generated_plan = demo_business_plan_template(form_data)

    return render_template("business_plan.html", form_data=form_data, generated_plan=generated_plan)


@business_bp.route("/business-plan/save", methods=["POST"])
@login_required
def save_business_plan():
    business_name = request.form.get("business_name", "").strip()
    business_type = request.form.get("business_type", "").strip()
    budget = request.form.get("budget", "0").strip()
    target_market = request.form.get("target_customers", "").strip()
    content = request.form.get("content", "").strip()

    try:
        budget_val = float(budget) if budget else None
    except ValueError:
        budget_val = None

    if not content:
        flash("Nothing to save — please generate a plan first.", "warning")
        return render_template("business_plan.html", form_data={}, generated_plan=None)

    plan = BusinessPlan(
        user_id=session["user_id"], business_name=business_name or "Untitled Business",
        business_type=business_type or "General", budget=budget_val,
        target_market=target_market, content=content,
    )
    db.session.add(plan)
    db.session.commit()
    flash("Business plan saved successfully!", "success")

    return render_template("business_plan.html", form_data={}, generated_plan=content, saved=True)


@business_bp.route("/market-analysis", methods=["GET", "POST"])
@login_required
def market_analysis():
    analysis_result = None
    form_data = {}

    if request.method == "POST":
        business_type = request.form.get("business_type", "").strip()
        location = request.form.get("location", "").strip()
        target_customers = request.form.get("target_customers", "").strip()
        budget = request.form.get("budget", "").strip()
        product = request.form.get("product", "").strip()

        form_data = {
            "business_type": business_type, "location": location,
            "target_customers": target_customers, "budget": budget, "product": product,
        }

        if not business_type or not location:
            flash("Business type and location are required.", "danger")
            return render_template("market_analysis.html", form_data=form_data, result=None)
            
        if budget:
            try:
                b_val = float(budget)
                if b_val <= 0:
                    flash("Invalid budget.", "danger")
                    return render_template("market_analysis.html", form_data=form_data, result=None)
            except ValueError:
                flash("Invalid budget.", "danger")
                return render_template("market_analysis.html", form_data=form_data, result=None)

        # Demo Mode / fallback template (kept simple + structured; labeled as AI/demo insight)
        analysis_result = demo_market_analysis_template(form_data)

    return render_template("market_analysis.html", form_data=form_data, result=analysis_result)

"""
routes/analyzer.py
-------------------
The Business Decision Support modules that differentiate this project from
a generic chatbot:

    GET/POST /business-analyzer         -> Business Profile input -> full analysis
    GET      /business-analyzer/<id>    -> view a saved analysis + What-If simulator
    GET      /my-businesses             -> saved Business Profile history
    POST     /my-businesses/<id>/delete -> delete a saved profile
    GET/POST /idea-generator            -> ML-scored Business Idea Generator
    GET/POST /competitor-analysis       -> simple competitor comparison tool
"""

from flask import Blueprint, render_template, request, session, flash, redirect, url_for

from database.database import db
from database.models import BusinessProfile, Prediction
from routes.auth import login_required
from ml.feasibility import compute_feasibility, compute_health_score
from ml.predict import predict_risk, explain_prediction, ModelNotTrainedError
from ml.idea_generator import generate_ideas

analyzer_bp = Blueprint("analyzer", __name__)

LEVELS = ["Low", "Medium", "High"]
BUSINESS_TYPES = ["Retail", "Food & Beverage", "E-commerce", "Services",
                   "Manufacturing", "Technology", "Education", "Fashion & Clothing"]


def _target_market_size(startup_cost: float) -> str:
    if startup_cost < 200000:
        return "Small"
    elif startup_cost < 750000:
        return "Medium"
    return "Large"


@analyzer_bp.route("/business-analyzer", methods=["GET", "POST"])
@login_required
def business_analyzer():
    result = None
    form_data = {}
    error_message = None

    if request.method == "POST":
        try:
            form_data = {k: request.form.get(k, "") for k in [
                "business_name", "business_type", "location", "startup_cost",
                "target_customers", "expected_price_per_order", "expected_daily_customers",
                "num_employees", "avg_employee_cost", "monthly_rent",
                "raw_material_cost_per_month", "marketing_budget_per_month",
                "other_monthly_expenses", "business_experience", "market_demand", "competition",
            ]}

            required = ["business_name", "business_type", "startup_cost",
                        "expected_price_per_order", "expected_daily_customers"]
            if not all(form_data.get(f) for f in required):
                flash("Please fill in all required fields.", "danger")
                raise ValueError("missing fields")

            startup_cost = float(form_data["startup_cost"])
            if startup_cost <= 0:
                flash("Invalid budget.", "danger")
                raise ValueError("invalid budget")
            expected_price = float(form_data["expected_price_per_order"])
            expected_daily_customers = float(form_data["expected_daily_customers"])
            num_employees = int(form_data.get("num_employees") or 0)
            avg_employee_cost = float(form_data.get("avg_employee_cost") or 0)
            monthly_rent = float(form_data.get("monthly_rent") or 0)
            raw_material_cost = float(form_data.get("raw_material_cost_per_month") or 0)
            marketing_budget = float(form_data.get("marketing_budget_per_month") or 0)
            if marketing_budget < 0:
                flash("Invalid budget.", "danger")
                raise ValueError("invalid budget")
            other_expenses = float(form_data.get("other_monthly_expenses") or 0)
            experience = form_data.get("business_experience") or "Medium"
            market_demand = form_data.get("market_demand") or "Medium"
            competition = form_data.get("competition") or "Medium"

            # 1. Financial Feasibility Engine (deterministic, real math)
            feasibility = compute_feasibility(
                startup_cost=startup_cost, monthly_rent=monthly_rent,
                raw_material_cost_per_month=raw_material_cost,
                marketing_budget_per_month=marketing_budget,
                other_monthly_expenses=other_expenses, num_employees=num_employees,
                avg_employee_cost=avg_employee_cost, expected_price_per_order=expected_price,
                expected_daily_customers=expected_daily_customers,
            )

            # 2. ML Risk Prediction (real trained Random Forest)
            operating_cost = feasibility["monthly_cost"]
            target_market = _target_market_size(startup_cost)
            try:
                prediction = predict_risk(
                    business_type=form_data["business_type"], investment=startup_cost,
                    market_demand=market_demand, competition=competition,
                    experience=experience, operating_cost=operating_cost,
                    target_market=target_market,
                )
                predicted_risk = prediction["predicted_risk"]
                risk_explanation = explain_prediction(
                    business_type=form_data["business_type"], investment=startup_cost,
                    market_demand=market_demand, competition=competition,
                    experience=experience, operating_cost=operating_cost,
                    target_market=target_market,
                )
            except ModelNotTrainedError:
                predicted_risk = "Unknown"
                risk_explanation = []

            # 3. Business Health Score (transparent weighted combination)
            health = compute_health_score(feasibility, predicted_risk, competition, market_demand)

            result = {
                "feasibility": feasibility, "predicted_risk": predicted_risk,
                "risk_explanation": risk_explanation, "health": health,
            }

            # Save as a Business Profile ("My Businesses")
            profile = BusinessProfile(
                user_id=session["user_id"], business_name=form_data["business_name"],
                business_type=form_data["business_type"], location=form_data.get("location"),
                startup_cost=startup_cost, target_customers=form_data.get("target_customers"),
                expected_price_per_order=expected_price, expected_daily_customers=expected_daily_customers,
                num_employees=num_employees, avg_employee_cost=avg_employee_cost,
                monthly_rent=monthly_rent, raw_material_cost_per_month=raw_material_cost,
                marketing_budget_per_month=marketing_budget, other_monthly_expenses=other_expenses,
                business_experience=experience, market_demand=market_demand, competition=competition,
                monthly_revenue=feasibility["monthly_revenue"], monthly_cost=feasibility["monthly_cost"],
                net_profit=feasibility["net_profit"], profit_margin_pct=feasibility["profit_margin_pct"],
                roi_pct=feasibility["roi_pct"], breakeven_months=feasibility["breakeven_months"],
                predicted_risk=predicted_risk, overall_health_score=health["overall_score"],
                financial_score=health["financial_score"], risk_score=health["risk_score"],
                competition_score=health["competition_score"], market_score=health["market_score"],
                growth_score=health["growth_score"],
            )
            db.session.add(profile)

            # Also store a Prediction record so Risk Prediction and Dashboard metrics update immediately
            pred_record = Prediction(
                user_id=session["user_id"],
                business_type=form_data["business_type"],
                investment=startup_cost,
                market_demand=market_demand,
                competition=competition,
                experience=experience,
                operating_cost=operating_cost,
                target_market_size=target_market,
                predicted_risk=predicted_risk,
            )
            db.session.add(pred_record)
            db.session.commit()
            result["saved_id"] = profile.id

        except ValueError:
            pass
        except Exception:
            error_message = "Something went wrong while analyzing this business. Please check your inputs."

    return render_template(
        "business_analyzer.html", business_types=BUSINESS_TYPES, levels=LEVELS,
        form_data=form_data, result=result, error_message=error_message,
    )


@analyzer_bp.route("/business-analyzer/<int:profile_id>")
@login_required
def view_business_profile(profile_id):
    profile = BusinessProfile.query.filter_by(id=profile_id, user_id=session["user_id"]).first()
    if not profile:
        flash("Business profile not found.", "danger")
        return redirect(url_for("analyzer.my_businesses"))
    return render_template("business_profile_detail.html", profile=profile)


@analyzer_bp.route("/my-businesses")
@login_required
def my_businesses():
    profiles = (
        BusinessProfile.query.filter_by(user_id=session["user_id"])
        .order_by(BusinessProfile.created_at.desc())
        .all()
    )
    return render_template("my_businesses.html", profiles=profiles)


@analyzer_bp.route("/my-businesses/<int:profile_id>/delete", methods=["POST"])
@login_required
def delete_business_profile(profile_id):
    profile = BusinessProfile.query.filter_by(id=profile_id, user_id=session["user_id"]).first()
    if profile:
        db.session.delete(profile)
        db.session.commit()
        flash("Business profile deleted.", "info")
    return redirect(url_for("analyzer.my_businesses"))


@analyzer_bp.route("/idea-generator", methods=["GET", "POST"])
@login_required
def idea_generator():
    ideas = None
    form_data = {}

    if request.method == "POST":
        budget = request.form.get("budget", "")
        keywords_raw = request.form.get("keywords", "")
        experience = request.form.get("experience", "Medium")
        form_data = {"budget": budget, "keywords": keywords_raw, "experience": experience}

        try:
            budget_val = float(budget)
            if budget_val <= 0:
                raise ValueError()
            keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
            ideas = generate_ideas(budget=budget_val, keywords=keywords, experience=experience, top_n=4)
        except ValueError:
            flash("Invalid budget.", "danger")

    return render_template("idea_generator.html", form_data=form_data, ideas=ideas)


@analyzer_bp.route("/competitor-analysis", methods=["GET", "POST"])
@login_required
def competitor_analysis():
    competitors = None
    form_data = {}

    if request.method == "POST":
        names = request.form.getlist("competitor_name")
        prices = request.form.getlist("competitor_price")
        strengths = request.form.getlist("competitor_strength")
        weaknesses = request.form.getlist("competitor_weakness")
        your_differentiator = request.form.get("your_differentiator", "").strip()

        form_data = {"your_differentiator": your_differentiator}

        competitors = []
        for name, price, strength, weakness in zip(names, prices, strengths, weaknesses):
            if name.strip():
                competitors.append({
                    "name": name.strip(), "price": price.strip(),
                    "strength": strength.strip(), "weakness": weakness.strip(),
                })

        if not competitors:
            flash("Please enter at least one competitor.", "danger")
            competitors = None

    return render_template("competitor_analysis.html", competitors=competitors, form_data=form_data)

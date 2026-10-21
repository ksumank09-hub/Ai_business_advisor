"""
routes/chatbot.py
------------------
The AI Business Assistant chat interface:
    GET  /chat            -> render chat UI + conversation list
    POST /chat             -> handle a message via NLP + RAG + LLM
    GET  /chat/<conv_id>    -> open a specific past conversation
    POST /chat/new          -> start a new conversation
    GET  /history            -> list all conversations
    DELETE /history/<id>     -> delete a conversation
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
import re

from database.database import db
from database.models import Conversation, Message, BusinessProfile
from routes.auth import login_required
from ai.nlp import analyze_query, INTENT_LABELS
from ai.rag import get_retriever
from ai.llm import generate_business_response
from config import Config


def _get_profile_context(user_id: int) -> str:
    """
    If the user has saved a Business Profile (via the Business Analyzer),
    summarize it as extra context so the AI Consultant can answer with
    the user's ACTUAL numbers instead of generic advice. This is what
    connects the chatbot to the rest of the system rather than leaving it
    as a standalone generic chat.
    """
    profile = (
        BusinessProfile.query.filter_by(user_id=user_id)
        .order_by(BusinessProfile.created_at.desc())
        .first()
    )
    if not profile:
        return ""
    loc_str = f" located in '{profile.location}'," if profile.location else ""
    return (
        f"The user has a saved business profile: '{profile.business_name}' "
        f"({profile.business_type}){loc_str} startup cost {profile.startup_cost}, "
        f"monthly revenue {profile.monthly_revenue}, monthly cost {profile.monthly_cost}, "
        f"net profit {profile.net_profit}, ML-predicted risk: {profile.predicted_risk}, "
        f"Business Health Score: {profile.overall_health_score}/100. "
        f"If relevant to the question, reference these actual numbers and location context instead of generic figures."
    )

chatbot_bp = Blueprint("chatbot", __name__)


@chatbot_bp.route("/chat", methods=["GET"])
@login_required
def chat_home():
    user_id = session["user_id"]
    conversations = (
        Conversation.query.filter_by(user_id=user_id)
        .order_by(Conversation.created_at.desc())
        .all()
    )

    conv_id = request.args.get("conv_id", type=int)
    active_conversation = None
    messages = []

    if conv_id:
        active_conversation = Conversation.query.filter_by(id=conv_id, user_id=user_id).first()
        if active_conversation:
            messages = active_conversation.messages
    elif conversations:
        active_conversation = conversations[0]
        messages = active_conversation.messages

    return render_template(
        "chatbot.html",
        conversations=conversations,
        active_conversation=active_conversation,
        messages=messages,
        demo_mode=Config.DEMO_MODE,
    )


@chatbot_bp.route("/chat/new", methods=["POST"])
@login_required
def new_conversation():
    user_id = session["user_id"]
    conversation = Conversation(user_id=user_id, title="New Conversation")
    db.session.add(conversation)
    db.session.commit()
    return redirect(url_for("chatbot.chat_home", conv_id=conversation.id))


@chatbot_bp.route("/chat", methods=["POST"])
@login_required
def send_message():
    user_id = session["user_id"]
    user_query = request.form.get("message", "").strip()
    conv_id = request.form.get("conv_id", type=int)

    if not user_query:
        flash("Please type a question before sending.", "warning")
        return redirect(url_for("chatbot.chat_home", conv_id=conv_id))

    if re.search(r'\bbudget\b[^\d]*?(?:-\d+|\b0\b)', user_query.lower()):
        flash("Invalid budget.", "danger")
        return redirect(url_for("chatbot.chat_home", conv_id=conv_id))

    # get or create conversation
    conversation = None
    if conv_id:
        conversation = Conversation.query.filter_by(id=conv_id, user_id=user_id).first()
    if conversation is None:
        title = user_query[:50] + ("..." if len(user_query) > 50 else "")
        conversation = Conversation(user_id=user_id, title=title)
        db.session.add(conversation)
        db.session.commit()

    source_list = []
    try:
        # 1. NLP: clean, tokenize, classify intent
        nlp_result = analyze_query(user_query)
        intent = nlp_result["intent"]

        # 2. RAG: retrieve relevant knowledge base context (kept as real
        #    structured results, not just a flattened string, so we can
        #    show the actual source filenames as citations in the UI)
        retriever = get_retriever()
        retrieved = retriever.retrieve(user_query, top_k=3)
        context = retriever.retrieve_as_context(user_query, top_k=3)
        source_list = sorted(set(r["source"] for r in retrieved))

        # 2b. Connect to the user's saved Business Profile, if any, so the
        #     assistant can reference the user's own numbers (see
        #     _get_profile_context above) instead of only generic advice.
        profile_context = _get_profile_context(user_id)
        if profile_context:
            context = (profile_context + "\n\n" + context) if context else profile_context

        # 3. LLM (or demo fallback): generate structured response
        llm_result = generate_business_response(user_query, intent, context)
        ai_response_text = llm_result["response"]

    except Exception as exc:
        # Never crash the app because of an AI/NLP/RAG failure
        ai_response_text = (
            "Sorry, something went wrong while generating a response. "
            "Please try rephrasing your question."
        )
        intent = "GENERAL_ADVICE"

    sources_str = ", ".join(source_list) if source_list else None

    # save both messages
    user_msg = Message(conversation_id=conversation.id, sender="user",
                        message=user_query, category=INTENT_LABELS.get(intent, intent))
    ai_msg = Message(conversation_id=conversation.id, sender="ai",
                      message=ai_response_text, category=INTENT_LABELS.get(intent, intent),
                      sources=sources_str)
    try:
        db.session.add_all([user_msg, ai_msg])
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        print(f"Error saving chat messages: {exc}")
        flash("Could not save message history.", "warning")

    return redirect(url_for("chatbot.chat_home", conv_id=conversation.id))


@chatbot_bp.route("/chat/delete/<int:conv_id>", methods=["POST"])
@login_required
def delete_chat(conv_id):
    user_id = session["user_id"]
    conversation = Conversation.query.filter_by(id=conv_id, user_id=user_id).first()
    if conversation:
        db.session.delete(conversation)
        db.session.commit()
        flash("Conversation deleted.", "info")
    return redirect(url_for("chatbot.chat_home"))


@chatbot_bp.route("/chat/clear", methods=["POST"])
@login_required
def clear_conversations():
    user_id = session["user_id"]
    conversations = Conversation.query.filter_by(user_id=user_id).all()
    for conv in conversations:
        db.session.delete(conv)
    db.session.commit()
    flash("All conversation history cleared.", "success")
    return redirect(url_for("chatbot.chat_home"))


@chatbot_bp.route("/history")
@login_required
def history():
    user_id = session["user_id"]
    conversations = (
        Conversation.query.filter_by(user_id=user_id)
        .order_by(Conversation.created_at.desc())
        .all()
    )
    return render_template("history.html", conversations=conversations)


@chatbot_bp.route("/history/<int:conv_id>", methods=["DELETE", "POST"])
@login_required
def delete_conversation(conv_id):
    user_id = session["user_id"]
    conversation = Conversation.query.filter_by(id=conv_id, user_id=user_id).first()
    if conversation:
        db.session.delete(conversation)
        db.session.commit()
        flash("Conversation deleted.", "info")
    else:
        flash("Conversation not found.", "danger")
    return redirect(url_for("chatbot.history"))

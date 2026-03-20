from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from src.database.session import SessionLocal
from src.database.models import User
from src.security.jwt import create_access_token
import bcrypt

auth_bp = Blueprint("auth", __name__)

@auth_bp.post("/signup")
def signup():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    db = SessionLocal()
    new_user = User(username=username, hashed_password=hashed_pw)

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return jsonify({
            "message": "User created successfully",
            "user_id": new_user.id
        }), 200

    except IntegrityError:
        db.rollback()
        return jsonify({"error": "Username already exists"}), 409

    finally:
        db.close()


@auth_bp.post("/login")
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    db = SessionLocal()
    stmt = select(User).where(User.username == username)
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    if not bcrypt.checkpw(password.encode(), user.hashed_password.encode()):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(user_id=user.id)

    return jsonify({
        "token": token,
        "user_id": user.id
    }), 200

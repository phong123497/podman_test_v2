import os
import json
from typing import List
from flask import Blueprint, jsonify, request
import mysql.connector
import faiss
import numpy as np


bp = Blueprint("main", __name__)


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "mysql"),
        user=os.getenv("MYSQL_USER", "appuser"),
        password=os.getenv("MYSQL_PASSWORD", "apppassword"),
        database=os.getenv("MYSQL_DATABASE", "appdb"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
    )


@bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@bp.get("/db-ping")
def db_ping():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        _ = cursor.fetchone()
        cursor.close()
        conn.close()
        return jsonify({"db": "ok"})
    except Exception as exc:  # intentionally broad for demo visibility
        return jsonify({"db": "error", "detail": str(exc)}), 500


@bp.post("/faiss/search")
def faiss_search():
    body = request.get_json(silent=True) or {}
    dim = int(body.get("dim", 4))
    k = int(body.get("k", 2))

    # Build a tiny FAISS index in-memory for demo
    np.random.seed(0)
    xb: np.ndarray = np.random.random((10, dim)).astype("float32")
    index = faiss.IndexFlatL2(dim)
    index.add(xb)

    # Query vector
    xq: np.ndarray = np.random.random((1, dim)).astype("float32")
    distances, neighbors = index.search(xq, k)

    return jsonify(
        {
            "dim": dim,
            "k": k,
            "neighbors": neighbors.tolist(),
            "distances": distances.tolist(),
            "query": xq.tolist(),
        }
    )


def create_wsgi_app():
    # For WSGI servers like gunicorn
    from . import create_app

    return create_app()


if __name__ == "__main__":
    from flask import Flask

    app: Flask = create_wsgi_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)



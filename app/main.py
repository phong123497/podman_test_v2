import os
import json
from typing import List
from flask import Blueprint, jsonify, request
import mysql.connector
import faiss
import numpy as np


bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    """Root endpoint - API information"""
    return jsonify({
        "name": "Podman CI/CD Deployment API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "GET /health - Health check",
            "db_ping": "GET /db-ping - MySQL connection test",
            "faiss_search": "POST /faiss/search - FAISS vector search"
        },
        "docs": "See README.md for more information"
    })


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


if __name__ == "__main__":
    # For development: run directly from this file
    # In production, use wsgi.py with gunicorn
    import sys
    import os
    # Add parent directory to path for imports
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app import create_app
    
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)



from datetime import datetime
from app.aplication import db


class VectorStoreRecord(db.Model):
    """Stores each Vector Store ID created in OpenAI with created_at."""
    __tablename__ = "vector_store_record"

    id = db.Column(db.Integer, primary_key=True)
    vector_store_id = db.Column(db.String(128), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<VectorStoreRecord {self.vector_store_id} @ {self.created_at}>"

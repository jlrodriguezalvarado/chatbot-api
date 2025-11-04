from app.aplication import db

class ApiKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    key = db.Column(db.String(128), unique=True)

    def __repr__(self):
        return f'<ApiKey {self.name}>'

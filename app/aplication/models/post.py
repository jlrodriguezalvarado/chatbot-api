from app.aplication import db


class Post(db.Model):
    """Stores wine/product content for Vector Store and optional full wine data from WP."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    wp_id = db.Column(db.Integer, nullable=True, index=True, comment='WordPress/WooCommerce product ID')
    product_url = db.Column(db.String(512), nullable=True, comment='Full product URL on WordPress')
    wine_data = db.Column(db.JSON, nullable=True, comment='Full wine payload from xtrawine schema')

    def __repr__(self):
        return f'<Post {self.title}>'

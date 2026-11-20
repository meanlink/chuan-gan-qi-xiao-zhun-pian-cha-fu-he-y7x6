from sqlalchemy import inspect, text
from src.config.database import Base, engine
from src import models
def migrate():
    Base.metadata.create_all(engine)
    # 既有库补充新增列；create_all 只建缺失的表，不会加列。
    with engine.begin() as conn:
        columns = [c['name'] for c in inspect(conn).get_columns('jobs')]
        if 'released' not in columns:
            conn.execute(text('ALTER TABLE jobs ADD COLUMN released BOOLEAN NOT NULL DEFAULT FALSE'))
if __name__=='__main__':migrate()

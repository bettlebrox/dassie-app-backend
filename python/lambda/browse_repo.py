from contextlib import closing
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from models.models import Browsed
from models.browse import Browse
from repos import BasePostgresRepository


class BrowseRepository(BasePostgresRepository):
    def __init__(self, username, password, dbname, db_cluster_endpoint):
        super().__init__(username, password, dbname, db_cluster_endpoint)
        self.model = Browse

    def get_by_tab_id(self, tab_id):
        with closing(self._session()) as session:
            return (
                session.query(self.model)
                .options(joinedload(Browse._articles))
                .filter_by(_tab_id=tab_id)
                .first()
            )

    def get_recently_browsed(self, limit: int = 10, days=7, hours=0):
        with closing(self._session()) as session:
            cut_off_date = datetime.now() - timedelta(days=days, hours=hours)
            subquery = (
                session.query(
                    Browsed._browse_id,
                )
                .filter(Browsed._logged_at > cut_off_date)
                .subquery()
            )

            return (
                session.query(self.model)
                .join(subquery, self.model._id == subquery.c._browse_id)
                .options(joinedload(Browse._articles))
                .limit(limit)
                .all()
            )

    def get_or_insert(self, model):
        existing = self.get_by_tab_id(model.tab_id)
        if existing is None:
            return self.add(model)
        else:
            return existing

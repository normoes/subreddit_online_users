from sqlalchemy import create_engine
from sqlalchemy import (
    Table,
    Column,
    DateTime,
    Integer,
    String,
    MetaData,
)
from sqlalchemy.orm import sessionmaker
import datetime
import logging

logging.basicConfig(
    format="%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%d-%m-%Y:%H:%M:%S",
)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

SQLITE = "sqlite"
POSTGRES = "postgres"

SUBREDDITS = "subreddits"
tables = SUBREDDITS


class Db:
    """Wrapper for database interactons
    """

    # http://docs.sqlalchemy.org/en/latest/core/engines.html
    DB_ENGINE = {SQLITE: "sqlite:///{DB}", POSTGRES: "postgres://{DB}"}

    db_engine = None

    def __init__(self, dbtype=SQLITE, dbname="data.db"):
        dbtype = dbtype.lower()
        if dbtype in self.DB_ENGINE.keys():
            engine_url = self.DB_ENGINE[dbtype].format(DB=dbname)
            self.db_engine = create_engine(engine_url, echo=False)
            log.warn(self.db_engine)
            try:
                self.metadata = MetaData(self.db_engine, reflect=True)
                self.create_db_tables()
            except (Exception) as e:
                log.error(str(e))
                raise e
        else:
            log.error("DBType is not found in DB_ENGINE")

    def insert_(self, table, args):
        if table not in tables:
            raise ValueError("Table unknown: {}".format(table))
        log.debug(
            "Insert {args} into table {table}".format(table=table, args=args)
        )
        table_ = self.metadata.tables.get(table, None)
        # table_ = Table(table, self.metadata, autoload=True)
        with self.db_engine.connect() as connection:
            try:
                statement = table_.insert().values(args)
                connection.execute(statement)
            except Exception as e:
                log.exception(e)

    def create_db_tables(self):
        """Create database table

        This can be called to create non-existent tables.
        This can also be called should the table already exist.
        """
        self.subreddits = Table(
            SUBREDDITS,
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("subreddit", String),
            Column("subscribers", String),
            Column("users_online", String),
            Column("created", DateTime, default=datetime.datetime.now()),
            extend_existing=True,
        )
        try:
            self.metadata.create_all()
            log.info("Tables created")
        except Exception as e:
            log.error("Error occurred during Table creation!")
            log.exception(e)

    def session_query(self, query=None):
        session = sessionmaker()
        session.configure(bind=self.db_engine)
        s = session()
        try:
            return s.query(query).scalar()
        finally:
            s.close()
        return None

import logging
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import mongomock

logger = logging.getLogger(__name__)

class DatabaseManager:
    _instance = None
    client = None
    db = None
    is_mock = False

    @classmethod
    def get_db(cls, mongo_uri="mongodb://127.0.0.1:27017/alphabetai_db", db_name="alphabetai_db"):
        if cls.db is not None:
            return cls.db

        try:
            real_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=1500)
            # Trigger connection check
            real_client.server_info()
            cls.client = real_client
            cls.db = real_client[db_name]
            cls.is_mock = False
            logger.info("Connected to live MongoDB server successfully.")
        except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as err:
            logger.warning("Live MongoDB not reachable (%s). Falling back to resilient mongomock in-memory database.", err)
            cls.client = mongomock.MongoClient()
            cls.db = cls.client[db_name]
            cls.is_mock = True

        cls.init_indexes()
        return cls.db

    @classmethod
    def init_indexes(cls):
        if cls.db is None:
            return

        try:
            # 1. users: unique username
            cls.db.users.create_index([("username", ASCENDING)], unique=True)
            
            # 2. students: unique student_id; unique roll_number within (class_id, section)
            cls.db.students.create_index([("student_id", ASCENDING)], unique=True)
            cls.db.students.create_index([
                ("class_id", ASCENDING),
                ("section", ASCENDING),
                ("roll_number", ASCENDING)
            ], unique=True)
            cls.db.students.create_index([("normalized_name", ASCENDING)])
            cls.db.students.create_index([("is_active", ASCENDING)])

            # 3. face_enrollments: unique student_id
            cls.db.face_enrollments.create_index([("student_id", ASCENDING)], unique=True)

            # 4. attendance_sessions
            cls.db.attendance_sessions.create_index([
                ("class_id", ASCENDING),
                ("section", ASCENDING),
                ("session_date", ASCENDING)
            ])

            # 5. attendance_records: CRITICAL unique constraint preventing duplicate attendance submissions
            cls.db.attendance_records.create_index([
                ("session_id", ASCENDING),
                ("student_id", ASCENDING)
            ], unique=True)
            cls.db.attendance_records.create_index([("student_id", ASCENDING)])
            cls.db.attendance_records.create_index([("timestamp", DESCENDING)])

            # 6. audit_logs
            cls.db.audit_logs.create_index([("timestamp", DESCENDING)])
            cls.db.audit_logs.create_index([("actor_id", ASCENDING)])
            
            logger.info("Database indexes successfully ensured.")
        except Exception as e:
            logger.error("Error creating indexes: %s", e)

def get_db():
    from config import Config
    return DatabaseManager.get_db(Config.MONGO_URI, Config.DB_NAME)

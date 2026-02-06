from typing import List, Optional

from psycopg2.extras import Json

from src.core.database.postgres_repository import PostgresRepository
from src.core.database.postgres_session import PostgresDatabase
from src.modules.ai.ai_result.enums.ai_result_type import AIResultType
from src.modules.ai.ai_result.models.ai_result import AIResult
from src.modules.ai.ai_result.repositories.ai_result_repository import (
    AIResultRepository,
)


class PostgresAIResultRepository(PostgresRepository[AIResult], AIResultRepository):
    def __init__(self, db: PostgresDatabase):
        super().__init__(db, "app.ai_results", AIResult)

    def find_by_message(self, msg_id: str, limit: int = 100) -> List[AIResult]:
        return self.find_by({"msg_id": msg_id}, limit=limit)

    def find_by_feature(self, feature_id: str, limit: int = 100) -> List[AIResult]:
        return self.find_by({"feature_id": feature_id}, limit=limit)

    def find_recent_by_feature(self, feature_id: str, limit: int = 50) -> List[AIResult]:
        query = (
            f"SELECT * FROM {self.table_name} WHERE feature_id = %s "
            "ORDER BY processed_at DESC "
            "LIMIT %s"
        )
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(query, (feature_id, limit))
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description]
                return [self.model_class(**dict(zip(cols, r))) for r in rows]
            finally:
                cur.close()

    def create_result(
        self,
        msg_id: str,
        feature_id: str,
        result_json: dict,
        result_type: AIResultType = AIResultType.AGENT_LOG,
        correlation_id: Optional[str] = None,
    ) -> Optional[AIResult]:
        data = {
            "msg_id": msg_id,
            "feature_id": feature_id,
            "result_json": Json(result_json),
            "result_type": (
                result_type.value if hasattr(result_type, "value") else result_type
            ),
        }
        if correlation_id:
            data["correlation_id"] = correlation_id
        return self.create(data)

    def delete_older_than(self, days: int) -> int:
        # Use make_interval for safer interval construction and self.table_name for correct schema
        query = (
            f"DELETE FROM {self.table_name} "
            "WHERE processed_at < NOW() - make_interval(days => %s)"
        )
        with self.db.connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(query, (days,))
                conn.commit()
                return cur.rowcount
            finally:
                cur.close()


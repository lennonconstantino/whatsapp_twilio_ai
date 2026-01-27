from datetime import datetime, date
from typing import List, Optional

from src.core.database.session import get_db
from src.core.database.supabase_repository import SupabaseRepository
from src.core.utils.logging import get_logger
from src.modules.ai.engines.lchain.feature.relationships.models.models import (
    Person, PersonCreate, PersonUpdate,
    Interaction, InteractionCreate, InteractionUpdate,
    Reminder, ReminderCreate, ReminderUpdate
)

logger = get_logger(__name__)


def prepare_data_for_db(data: dict) -> dict:
    """
    Prepara dados Pydantic para inserção no Supabase.
    Converte datetime/date para ISO string.
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, (datetime, date)):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


class PersonRepository(SupabaseRepository[Person]):
    """Repository para operações de Person"""

    def __init__(self):
        super().__init__(
            client=get_db(),
            table_name="person",
            model_class=Person,
            validates_ulid=False,
        )

    def create_from_schema(self, person: PersonCreate) -> Optional[Person]:
        """Cria person a partir do schema Pydantic"""
        data = prepare_data_for_db(person.model_dump())
        return self.create(data)

    def update_from_schema(
        self, person_id: int, person: PersonUpdate
    ) -> Optional[Person]:
        """Atualiza person a partir do schema Pydantic"""
        data = prepare_data_for_db(person.model_dump(exclude_unset=True))
        if not data:
            return self.find_by_id(person_id)
        return self.update(person_id, data)

    def search_by_name_or_tags(self, name: Optional[str] = None, tags: Optional[str] = None) -> List[Person]:
        """Busca pessoas por nome ou tags"""
        try:
            query = self.client.table(self.table_name).select("*")
            
            if name:
                query = query.or_(f"first_name.ilike.%{name}%,last_name.ilike.%{name}%")
            
            if tags:
                query = query.ilike("tags", f"%{tags}%")
                
            result = query.execute()
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error(
                f"Error searching people",
                error=str(e),
                name=name,
                tags=tags
            )
            raise


class InteractionRepository(SupabaseRepository[Interaction]):
    """Repository para operações de Interaction"""

    def __init__(self):
        super().__init__(
            client=get_db(),
            table_name="interaction",
            model_class=Interaction,
            validates_ulid=False,
        )

    def create_from_schema(self, interaction: InteractionCreate) -> Optional[Interaction]:
        """Cria interaction a partir do schema Pydantic"""
        data = prepare_data_for_db(interaction.model_dump())
        return self.create(data)
    
    def search(self, person_id: Optional[int] = None, channel: Optional[str] = None, type_: Optional[str] = None) -> List[Interaction]:
        """Busca interações com filtros"""
        try:
            query = self.client.table(self.table_name).select("*")
            
            if person_id is not None:
                query = query.eq("person_id", person_id)
            if channel:
                query = query.eq("channel", channel)
            if type_:
                query = query.eq("type", type_)
                
            query = query.order("date", desc=True)
            result = query.execute()
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error(f"Error searching interactions", error=str(e))
            raise


class ReminderRepository(SupabaseRepository[Reminder]):
    """Repository para operações de Reminder"""

    def __init__(self):
        super().__init__(
            client=get_db(),
            table_name="reminder",
            model_class=Reminder,
            validates_ulid=False,
        )

    def create_from_schema(self, reminder: ReminderCreate) -> Optional[Reminder]:
        """Cria reminder a partir do schema Pydantic"""
        data = prepare_data_for_db(reminder.model_dump())
        return self.create(data)

    def get_upcoming(self, days: int = 7) -> List[Reminder]:
        """Busca lembretes para os próximos dias"""
        from datetime import timedelta
        
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days)
        
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .gte("due_date", start_date.isoformat())
                .lte("due_date", end_date.isoformat())
                .eq("status", "open")
                .order("due_date", desc=False)
                .execute()
            )
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error(f"Error getting upcoming reminders", error=str(e))
            raise


# Singleton instances
_person_repo: Optional[PersonRepository] = None
_interaction_repo: Optional[InteractionRepository] = None
_reminder_repo: Optional[ReminderRepository] = None


def get_person_repository() -> PersonRepository:
    global _person_repo
    if _person_repo is None:
        _person_repo = PersonRepository()
    return _person_repo


def get_interaction_repository() -> InteractionRepository:
    global _interaction_repo
    if _interaction_repo is None:
        _interaction_repo = InteractionRepository()
    return _interaction_repo


def get_reminder_repository() -> ReminderRepository:
    global _reminder_repo
    if _reminder_repo is None:
        _reminder_repo = ReminderRepository()
    return _reminder_repo

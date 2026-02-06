"""
Seed script for Relationships feature.
Populates initial data: people, interactions, and reminders.
"""

from datetime import datetime, date
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Add project root to path to allow importing src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.config import settings
from src.core.utils import get_logger
from src.core.di.container import Container
from src.modules.ai.engines.lchain.feature.relationships.models.models import (
    PersonCreate, InteractionCreate, ReminderCreate
)


logger = get_logger(__name__)

def get_repositories():
    """Get repositories from DI container."""
    if settings.database.backend == "supabase":
        # Check for Supabase Service Role Key to bypass RLS
        if settings.supabase.service_key:
            logger.info("Using Supabase Service Role Key for seeding (Bypassing RLS)...")
            settings.supabase.key = settings.supabase.service_key
        else:
            logger.warning("SUPABASE_SERVICE_KEY not found. Using Anon Key (might fail due to RLS).")

    container = Container()
    container.wire(modules=[__name__])
    
    person_repo = container.person_repository()
    interaction_repo = container.interaction_repository()
    reminder_repo = container.reminder_repository()
    
    return person_repo, interaction_repo, reminder_repo

def seed_people(person_repo):
    """
    Seed people data.
    Returns: Dict mapping mock_id -> created_person
    """
    logger.info("Seeding people...")

    # Dados do mock_data.py
    people_data = [
        {
            "mock_id": 1, 
            "first_name": "João", 
            "last_name": "Silva", 
            "phone": "+55 11 99999-1111", 
            "tags": "cliente,tech,startup", 
            "birthday": date(1985, 3, 15), 
            "city": "São Paulo", 
            "notes": "CEO da TechStart, interessado em soluções de IA"
        },
        {
            "mock_id": 2, 
            "first_name": "Maria", 
            "last_name": "Santos", 
            "phone": "+55 21 98888-2222", 
            "tags": "parceiro,design,creative", 
            "birthday": date(1990, 7, 22), 
            "city": "Rio de Janeiro", 
            "notes": "Designer freelancer, sempre pontual nos projetos"
        },
        {
            "mock_id": 3, 
            "first_name": "Carlos", 
            "last_name": "Oliveira", 
            "phone": "+55 31 97777-3333", 
            "tags": "fornecedor,logistica,confiável", 
            "birthday": date(1978, 11, 8), 
            "city": "Belo Horizonte", 
            "notes": "Proprietário da LogiFast, excelente serviço"
        },
        {
            "mock_id": 4, 
            "first_name": "Ana", 
            "last_name": "Costa", 
            "phone": "+55 41 96666-4444", 
            "tags": "investidor,financeiro,estratégico", 
            "birthday": date(1982, 5, 12), 
            "city": "Curitiba", 
            "notes": "Partner da Venture Capital, sempre busca inovação"
        },
        {
            "mock_id": 5, 
            "first_name": "Pedro", 
            "last_name": "Ferreira", 
            "phone": "+55 51 95555-5555", 
            "tags": "mentor,experiência,network", 
            "birthday": date(1975, 9, 30), 
            "city": "Porto Alegre", 
            "notes": "Ex-executivo da Microsoft, agora consultor independente"
        }
    ]

    person_map = {} # mock_id -> person object

    for data in people_data:
        mock_id = data.pop("mock_id")
        
        # Check by phone to avoid duplicates
        existing = person_repo.search_by_name_or_tags(name=None, tags=None) # TODO: Add get_by_phone to repo or use search
        # Using a simpler check logic since search_by_name_or_tags returns list
        # For this seed script, we will assume we can filter manually or just create if not found
        # Ideally repo should have get_by_phone
        
        # Let's try to find by phone manually since repo interface might be limited
        # In a real scenario, we should add get_by_phone to repository
        # For now, let's just create. Idempotency is tricky without unique constraints on phone in schema (not enforced in previous step but index exists)
        
        # Checking logic:
        # Since search_by_name_or_tags is what we have exposed, let's use it or just proceed.
        # But wait, we can use repo.find_by({"phone": ...}) inherited from SupabaseRepository
        
        existing_list = person_repo.find_by({"phone": data["phone"]}, limit=1)
        
        if existing_list:
            logger.info(f"Person {data['first_name']} {data['last_name']} already exists")
            person_map[mock_id] = existing_list[0]
        else:
            person_input = PersonCreate(**data)
            person = person_repo.create_from_schema(person_input)
            logger.info(f"Created person: {person.first_name} {person.last_name} (ID: {person.id})")
            person_map[mock_id] = person
            
    return person_map

def seed_interactions(interaction_repo, person_map):
    """
    Seed interaction data.
    """
    logger.info("Seeding interactions...")

    interactions_data = [
        {
            "mock_person_id": 1, 
            "date": datetime(2024, 1, 15, 14, 30), 
            "channel": "whatsapp", 
            "type": "consulta", 
            "summary": "João perguntou sobre integração com APIs de IA", 
            "sentiment": 0.8
        },
        {
            "mock_person_id": 1, 
            "date": datetime(2024, 1, 20, 10, 15), 
            "channel": "email", 
            "type": "proposta", 
            "summary": "Enviada proposta comercial para projeto de chatbot", 
            "sentiment": 0.9
        },
        {
            "mock_person_id": 2, 
            "date": datetime(2024, 1, 18, 16, 45), 
            "channel": "telefone", 
            "type": "reunião", 
            "summary": "Discussão sobre redesign da interface do usuário", 
            "sentiment": 0.7
        },
        {
            "mock_person_id": 3, 
            "date": datetime(2024, 1, 22, 9, 0), 
            "channel": "whatsapp", 
            "type": "negociação", 
            "summary": "Acordo sobre preços de entrega para próximos 6 meses", 
            "sentiment": 0.6
        },
        {
            "mock_person_id": 4, 
            "date": datetime(2024, 1, 25, 15, 20), 
            "channel": "zoom", 
            "type": "apresentação", 
            "summary": "Pitch para investimento em nova funcionalidade", 
            "sentiment": 0.85
        },
        {
            "mock_person_id": 5, 
            "date": datetime(2024, 1, 28, 11, 30), 
            "channel": "linkedin", 
            "type": "networking", 
            "summary": "Pedro compartilhou nosso post sobre inovação em IA", 
            "sentiment": 0.9
        }
    ]

    count = 0
    for data in interactions_data:
        mock_person_id = data.pop("mock_person_id")
        person = person_map.get(mock_person_id)
        
        if not person:
            logger.warning(f"Skipping interaction: Person mock_id={mock_person_id} not found")
            continue

        # Check duplicates (same person, same date)
        filters = {
            "person_id": person.id,
            "date": data["date"].isoformat()
        }
        existing = interaction_repo.find_by(filters, limit=1)
        
        if existing:
            continue

        data["person_id"] = person.id
        interaction_input = InteractionCreate(**data)
        interaction_repo.create_from_schema(interaction_input)
        count += 1
    
    logger.info(f"Created {count} interactions")

def seed_reminders(reminder_repo, person_map):
    """
    Seed reminder data.
    """
    logger.info("Seeding reminders...")

    reminders_data = [
        {
            "mock_person_id": 1, 
            "due_date": datetime(2024, 2, 5, 9, 0), 
            "reason": "Follow-up sobre proposta enviada", 
            "status": "open"
        },
        {
            "mock_person_id": 2, 
            "due_date": datetime(2024, 1, 30, 14, 0), 
            "reason": "Reunião de alinhamento do projeto de design", 
            "status": "completed"
        },
        {
            "mock_person_id": 3, 
            "due_date": datetime(2024, 2, 10, 16, 0), 
            "reason": "Renovação do contrato de logística", 
            "status": "open"
        },
        {
            "mock_person_id": 4, 
            "due_date": datetime(2024, 2, 15, 10, 0), 
            "reason": "Decisão sobre investimento", 
            "status": "open"
        },
        {
            "mock_person_id": 5, 
            "due_date": datetime(2024, 2, 1, 15, 30), 
            "reason": "Mentoria sobre estratégia de crescimento", 
            "status": "open"
        }
    ]

    count = 0
    for data in reminders_data:
        mock_person_id = data.pop("mock_person_id")
        person = person_map.get(mock_person_id)
        
        if not person:
            logger.warning(f"Skipping reminder: Person mock_id={mock_person_id} not found")
            continue

        # Check duplicates
        filters = {
            "person_id": person.id,
            "reason": data["reason"]
        }
        existing = reminder_repo.find_by(filters, limit=1)
        
        if existing:
            continue

        data["person_id"] = person.id
        reminder_input = ReminderCreate(**data)
        reminder_repo.create_from_schema(reminder_input)
        count += 1
        
    logger.info(f"Created {count} reminders")

def clear_relationships_data(person_repo, interaction_repo, reminder_repo):
    """
    Clear all relationships data.
    """
    logger.warning("CLEARING ALL RELATIONSHIPS DATA")
    
    # Delete interactions and reminders first (FKs)
    # Actually if CASCADE is set in DB, deleting person is enough, but explicit is better for logic
    # But repos usually don't have delete_all exposed easily without fetching.
    # We will rely on CASCADE or manual loop.
    
    # Simpler: just loop fetch and delete. Not efficient but safe for seed script.
    
    reminders = reminder_repo.find_all(limit=1000)
    for r in reminders:
        reminder_repo.delete(r.id)
        
    interactions = interaction_repo.find_all(limit=1000)
    for i in interactions:
        interaction_repo.delete(i.id)
        
    people = person_repo.find_all(limit=1000)
    for p in people:
        person_repo.delete(p.id)
        
    logger.info("Relationships data cleared")

def main(clear_data: bool = False):
    logger.info("Starting relationships seed process...")
    
    try:
        # Repositories
        person_repo, interaction_repo, reminder_repo = get_repositories()
        
        if clear_data:
             response = input("WARNING: DELETE ALL relationships data? 'YES' to confirm: ")
             if response == "YES":
                 clear_relationships_data(person_repo, interaction_repo, reminder_repo)
             else:
                 return

        # 1. Seed People
        person_map = seed_people(person_repo)
        
        # 2. Seed Interactions
        seed_interactions(interaction_repo, person_map)
        
        # 3. Seed Reminders
        seed_reminders(reminder_repo, person_map)
        
        logger.info("Relationships seed process completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during seed process: {e}")
        raise

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed relationships data")
    parser.add_argument("--clear", action="store_true", help="Clear existing data before seeding")
    args = parser.parse_args()
    main(clear_data=args.clear)

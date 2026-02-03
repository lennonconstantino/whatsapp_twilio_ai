from datetime import datetime

def prepare_data_for_db(data: dict) -> dict:
    """
    Prepara dados Pydantic para inserção no Supabase.
    Converte datetime para ISO string.
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result

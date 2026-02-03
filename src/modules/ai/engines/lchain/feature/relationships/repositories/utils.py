from datetime import datetime, date

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

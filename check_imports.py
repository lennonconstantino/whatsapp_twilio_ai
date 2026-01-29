try:
    from langchain_community.vectorstores import SupabaseVectorStore
    from langchain_openai import OpenAIEmbeddings
    print("Imports successful")
except ImportError as e:
    print(f"Import failed: {e}")

### Detalhes da Implementação
- Implementa a interface IRepository completa ( create , find_by_id , update , delete , find_by , count ).
- Gerencia a conversão automática entre Modelos ORM (SQLAlchemy) e Modelos de Domínio (Pydantic) .
- Utiliza sqlalchemy.orm.Session para transações.
### Como Utilizar
Para usar esta implementação em vez do SupabaseRepository , será necessário:

1. Definir os modelos ORM (herdando de DeclarativeBase ) que mapeiam as tabelas do banco.
2. Configurar o container de injeção de dependência para injetar PostgresRepository passando a Session , a classe do modelo ORM e a classe do modelo Pydantic.
Exemplo conceitual:

```
# No container de DI
user_repository = providers.Factory(
    PostgresRepository,
    session=db_session,
    orm_model=UserORM,      # Modelo SQLAlchemy
    pydantic_model=User     # Modelo Pydantic
)
```

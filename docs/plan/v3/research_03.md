# Refatoração da classe IdentityService para suporte ao FeatureService

Refatorei a classe IdentityService para integrar plenamente o suporte a funcionalidades ( features ), permitindo tanto a verificação de acesso quanto a inicialização de features durante o registro.

### Alterações Realizadas
1. Enriquecimento do Contexto do Usuário ( get_user_context ) :
   
   - O método agora retorna também a lista de features habilitadas para a organização (Owner) do usuário. Isso elimina a necessidade de chamadas separadas para obter permissões.
2. Verificação de Acesso ( check_feature_access ) :
   
   - Adicionei este novo método utilitário para verificar de forma simples e direta se um usuário possui acesso a uma feature específica ( enabled=True ).
3. Registro com Features Iniciais ( register_organization ) :
   
   - Atualizei a assinatura para aceitar um parâmetro opcional initial_features: List[str] .
   - Agora é possível criar uma organização já com um conjunto de features ativadas (ex: "whatsapp", "ai_bot"), facilitando o onboarding.
### Código Refatorado
Aqui estão as principais mudanças em identity_service.py :

```python
    def register_organization(
        self, 
        owner_data: OwnerCreateDTO, 
        admin_user_data: UserCreateDTO,
        initial_features: Optional[List[str]] = None  # Novo 
        parâmetro
    ) -> Tuple[Optional[Owner], Optional[User]]:
        # ... (criação de owner e user) ...
            
        # 3. Cria features iniciais se fornecidas
        if initial_features:
            logger.info(f"Creating {len(initial_features)} initial 
            features for owner {owner.owner_id}")
            for feature_name in initial_features:
                try:
                    feature_dto = FeatureCreateDTO(
                        owner_id=owner.owner_id,
                        name=feature_name,
                        enabled=True,
                        description=f"Initial feature: 
                        {feature_name}"
                    )
                    self.feature_service.create_feature
                    (feature_dto)
                except Exception as e:
                    logger.error(f"Failed to create feature 
                    {feature_name}: {e}")
            
        return owner, user

    def get_user_context(self, user_id: str) -> Optional[Dict[str, 
    Any]]:
        # ... (busca user e owner) ...
        features = self.feature_service.get_enabled_features(owner.
        owner_id)
        
        return {
            "user": user,
            "owner": owner,
            "features": features  # Contexto enriquecido
        }

    def check_feature_access(self, user_id: str, feature_name: 
    str) -> bool:
        """
        Check if a user has access to a specific feature.
        """
        user = self.user_service.get_user_by_id(user_id)
        if not user:
            return False
            
        feature = self.feature_service.get_feature_by_name(user.
        owner_id, feature_name)
        return feature is not None and feature.enabled
```
### Relatório Técnico e Sugestões
A refatoração centralizou a lógica de acesso a features no IdentityService , promovendo coesão e facilitando o consumo por outras camadas da aplicação. Ao injetar as features no contexto do usuário, evitamos múltiplas consultas ao banco de dados em fluxos críticos de autorização.

Sugestão de Aprimoramento: Como get_user_context e check_feature_access tendem a ser chamados frequentemente (potencialmente a cada requisição), recomendo fortemente implementar uma camada de cache (como Redis) para essas consultas. Além disso, para um sistema em produção, considere definir "planos" ou "pacotes" de features em uma configuração centralizada, em vez de passar listas de strings soltas durante o registro.

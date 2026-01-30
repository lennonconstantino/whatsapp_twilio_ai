import unittest
from unittest.mock import MagicMock, patch
from src.modules.ai.memory.services.hybrid_memory_service import HybridMemoryService
from src.modules.conversation.models.message import Message
from src.modules.conversation.enums.message_owner import MessageOwner
from src.core.config.settings import settings

class TestMemoryIntegrationFlow(unittest.TestCase):
    """
    Testes de fluxo de integração (simulados) para validar o comportamento Read-Through.
    """
    def setUp(self):
        self.redis_repo = MagicMock()
        self.message_repo = MagicMock()
        self.vector_repo = MagicMock()
        
        self.service = HybridMemoryService(
            redis_repo=self.redis_repo,
            message_repo=self.message_repo,
            vector_repo=self.vector_repo
        )
        self.session_id = "integration_test_session"

    def test_full_read_through_flow(self):
        """
        Cenário:
        1. Redis vazio (Miss).
        2. Busca no DB (Hit).
        3. Popula Redis.
        4. Segunda chamada deve pegar do Redis (Simulado).
        """
        # --- Passo 1: Configurar Estado Inicial (Redis Vazio, DB com dados) ---
        
        # Redis retorna vazio inicialmente
        self.redis_repo.get_context.return_value = []
        
        # DB retorna uma mensagem
        mock_msg = MagicMock(spec=Message)
        mock_msg.message_owner = MessageOwner.USER
        mock_msg.body = "Mensagem Persistida"
        self.message_repo.find_recent_by_conversation.return_value = [mock_msg]

        # --- Passo 2: Primeira Chamada (Cache Miss) ---
        result_1 = self.service.get_context(self.session_id)
        
        # Validações Passo 2
        self.assertEqual(len(result_1), 1)
        self.assertEqual(result_1[0]["content"], "Mensagem Persistida")
        
        # Verifica se chamou DB
        self.message_repo.find_recent_by_conversation.assert_called_once()
        
        # Verifica se tentou popular o Redis
        self.redis_repo.add_message.assert_called_once()
        args, _ = self.redis_repo.add_message.call_args
        self.assertEqual(args[0], self.session_id)
        self.assertEqual(args[1]["content"], "Mensagem Persistida")

        # --- Passo 3: Simular Estado Pós-População (Redis agora tem dados) ---
        
        # Agora configuramos o mock do Redis para retornar o que foi "salvo"
        # Na vida real, o Redis teria persistido. Aqui simulamos o efeito colateral.
        saved_msg = args[1]
        self.redis_repo.get_context.return_value = [saved_msg]
        
        # Resetamos o mock do DB para garantir que NÃO será chamado
        self.message_repo.find_recent_by_conversation.reset_mock()

        # --- Passo 4: Segunda Chamada (Cache Hit) ---
        result_2 = self.service.get_context(self.session_id)

        # Validações Passo 4
        self.assertEqual(result_2, result_1) # Deve ser igual
        
        # Verifica se Redis foi chamado novamente
        # (get_context foi chamado 2 vezes no total)
        self.assertEqual(self.redis_repo.get_context.call_count, 2)
        
        # CRÍTICO: Verifica se o DB NÃO foi chamado desta vez
        self.message_repo.find_recent_by_conversation.assert_not_called()
        
        print("\n✅ Teste de Integração (Fluxo Read-Through) passou com sucesso!")

    def test_semantic_search_integration(self):
        """
        Cenário:
        1. Busca com query.
        2. Verifica se VectorRepo é consultado e resultado anexado.
        """
        # Redis retorna algo básico
        self.redis_repo.get_context.return_value = [{"role": "user", "content": "Oi"}]
        
        # Vector Repo retorna resultado relevante
        self.vector_repo.hybrid_search_relevant.return_value = [
            {"content": "O usuário mora em São Paulo", "metadata": {}}
        ]
        
        # Chamada com Query
        result = self.service.get_context(self.session_id, query="Onde eu moro?")
        
        # Validação
        if settings.memory.enable_hybrid_retrieval:
            self.vector_repo.hybrid_search_relevant.assert_called_once()
        else:
            self.vector_repo.vector_search_relevant.assert_called_once()
        
        # O primeiro item deve ser a info semântica (System Message)
        self.assertEqual(result[0]["role"], "system")
        self.assertIn("O usuário mora em São Paulo", result[0]["content"])
        
        # O segundo item deve ser a mensagem do histórico (Redis)
        self.assertEqual(result[1]["content"], "Oi")

        print("\n✅ Teste de Integração (Busca Semântica) passou com sucesso!")

if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""
Script de teste para validar a correção do bug de session_key duplicada.

Este script testa se a lógica de get_or_create_conversation está funcionando
corretamente ao enviar múltiplas mensagens consecutivas.

Uso:
    python test_conversation_fix.py
"""

import sys
import time
from datetime import datetime

import requests


class ConversationTester:
    """Tester para validar a correção do bug."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.webhook_url = f"{base_url}/channels/twilio/v1/webhooks/inbound"
        self.api_key = "your-api-key-here"  # Configure conforme necessário

    def build_payload(self, message: str, from_number: str, to_number: str):
        """Constrói payload de teste."""
        return {
            "MessageSid": f"SM_test_{int(time.time())}",
            "SmsMessageSid": f"SM_test_{int(time.time())}",
            "AccountSid": "AC_test",
            "Body": message,
            "MessageType": "text",
            "From": f"whatsapp:{from_number}",
            "To": f"whatsapp:{to_number}",
            "WaId": from_number.replace("+", ""),
            "ProfileName": "Test User",
            "NumMedia": "0",
            "NumSegments": "1",
            "SmsStatus": "received",
            "ApiVersion": "2010-04-01",
            "LocalSender": "True",
        }

    def send_message(self, message: str, from_number: str, to_number: str) -> dict:
        """Envia mensagem para o webhook."""
        payload = self.build_payload(message, from_number, to_number)
        headers = {"X-API-Key": self.api_key}

        try:
            response = requests.post(
                self.webhook_url, data=payload, headers=headers, timeout=30
            )

            return {
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "data": response.json() if response.status_code == 200 else None,
                "error": response.text if response.status_code != 200 else None,
            }
        except Exception as e:
            return {"status_code": 0, "success": False, "error": str(e)}

    def test_consecutive_messages(self, num_messages: int = 5):
        """
        Teste: Enviar múltiplas mensagens consecutivas.

        Expectativa: Todas as mensagens devem usar a MESMA conversa.
        """
        print(f"\n{'='*60}")
        print(f"TESTE 1: {num_messages} mensagens consecutivas")
        print(f"{'='*60}")

        from_number = "+14155238886"
        to_number = "+5511991490733"

        conv_ids = []

        for i in range(num_messages):
            message = f"Mensagem de teste #{i+1}"
            print(f"\n[{i+1}/{num_messages}] Enviando: {message}")

            result = self.send_message(message, from_number, to_number)

            if result["success"]:
                conv_id = result["data"].get("conv_id")
                conv_ids.append(conv_id)
                print(f"  ✅ Sucesso - conv_id: {conv_id}")
            else:
                print(f"  ❌ Erro: {result['error']}")
                return False

            time.sleep(0.5)  # Pequeno delay entre mensagens

        # Validar resultados
        print(f"\n{'='*60}")
        print("VALIDAÇÃO")
        print(f"{'='*60}")

        unique_convs = set(conv_ids)

        print(f"Total de mensagens enviadas: {num_messages}")
        print(f"Conv IDs únicos: {len(unique_convs)}")
        print(f"Conv IDs: {conv_ids}")

        if len(unique_convs) == 1:
            print("\n✅ TESTE PASSOU: Todas as mensagens usaram a mesma conversa!")
            return True
        else:
            print("\n❌ TESTE FALHOU: Múltiplas conversas foram criadas!")
            print(f"   Esperado: 1 conversa")
            print(f"   Obtido: {len(unique_convs)} conversas")
            return False

    def test_different_directions(self):
        """
        Teste: Mensagens em direções diferentes (A->B e B->A).

        Expectativa: Ambas devem usar a MESMA conversa (session_key bidirecional).
        """
        print(f"\n{'='*60}")
        print("TESTE 2: Mensagens bidirecionais")
        print(f"{'='*60}")

        number_a = "+14155238886"
        number_b = "+5511991490733"

        conv_ids = []

        # A -> B
        print("\n[1/4] A -> B")
        result = self.send_message("Hello from A", number_a, number_b)
        if result["success"]:
            conv_id = result["data"].get("conv_id")
            conv_ids.append(conv_id)
            print(f"  ✅ Sucesso - conv_id: {conv_id}")
        else:
            print(f"  ❌ Erro: {result['error']}")
            return False

        time.sleep(0.5)

        # B -> A (direção inversa)
        print("\n[2/4] B -> A")
        result = self.send_message("Hello from B", number_b, number_a)
        if result["success"]:
            conv_id = result["data"].get("conv_id")
            conv_ids.append(conv_id)
            print(f"  ✅ Sucesso - conv_id: {conv_id}")
        else:
            print(f"  ❌ Erro: {result['error']}")
            return False

        time.sleep(0.5)

        # A -> B novamente
        print("\n[3/4] A -> B (again)")
        result = self.send_message("Another from A", number_a, number_b)
        if result["success"]:
            conv_id = result["data"].get("conv_id")
            conv_ids.append(conv_id)
            print(f"  ✅ Sucesso - conv_id: {conv_id}")
        else:
            print(f"  ❌ Erro: {result['error']}")
            return False

        time.sleep(0.5)

        # B -> A novamente
        print("\n[4/4] B -> A (again)")
        result = self.send_message("Another from B", number_b, number_a)
        if result["success"]:
            conv_id = result["data"].get("conv_id")
            conv_ids.append(conv_id)
            print(f"  ✅ Sucesso - conv_id: {conv_id}")
        else:
            print(f"  ❌ Erro: {result['error']}")
            return False

        # Validar
        print(f"\n{'='*60}")
        print("VALIDAÇÃO")
        print(f"{'='*60}")

        unique_convs = set(conv_ids)

        print(f"Total de mensagens: 4 (2x A->B, 2x B->A)")
        print(f"Conv IDs únicos: {len(unique_convs)}")
        print(f"Conv IDs: {conv_ids}")

        if len(unique_convs) == 1:
            print("\n✅ TESTE PASSOU: Session key bidirecional funcionando!")
            return True
        else:
            print("\n❌ TESTE FALHOU: Múltiplas conversas para mesma session!")
            return False

    def test_idempotency(self):
        """
        Teste: Enviar mensagem duplicada (mesmo MessageSid).

        Expectativa: Deve retornar a mensagem existente, não criar duplicata.
        """
        print(f"\n{'='*60}")
        print("TESTE 3: Idempotência")
        print(f"{'='*60}")

        from_number = "+14155238886"
        to_number = "+5511991490733"

        # Usar MessageSid fixo
        message_sid = f"SM_idempotency_test_{int(time.time())}"

        payload = self.build_payload("Idempotency test", from_number, to_number)
        payload["MessageSid"] = message_sid

        headers = {"X-API-Key": self.api_key}

        # Primeira tentativa
        print("\n[1/2] Primeira tentativa")
        result1 = requests.post(self.webhook_url, data=payload, headers=headers)

        if result1.status_code == 200:
            data1 = result1.json()
            print(f"  ✅ Sucesso - msg_id: {data1.get('msg_id')}")
        else:
            print(f"  ❌ Erro: {result1.text}")
            return False

        time.sleep(0.5)

        # Segunda tentativa (mesma mensagem)
        print("\n[2/2] Segunda tentativa (duplicata)")
        result2 = requests.post(self.webhook_url, data=payload, headers=headers)

        if result2.status_code == 200:
            data2 = result2.json()
            print(f"  ✅ Sucesso - msg_id: {data2.get('msg_id')}")
        else:
            print(f"  ❌ Erro: {result2.text}")
            return False

        # Validar
        print(f"\n{'='*60}")
        print("VALIDAÇÃO")
        print(f"{'='*60}")

        msg_id_1 = data1.get("msg_id")
        msg_id_2 = data2.get("msg_id")

        print(f"MessageSid: {message_sid}")
        print(f"Primeira msg_id: {msg_id_1}")
        print(f"Segunda msg_id: {msg_id_2}")

        if msg_id_1 == msg_id_2:
            print("\n✅ TESTE PASSOU: Idempotência funcionando!")
            return True
        else:
            print("\n❌ TESTE FALHOU: Mensagens duplicadas criadas!")
            return False


def main():
    """Executa todos os testes."""
    print("=" * 60)
    print("TESTES DE VALIDAÇÃO - CORREÇÃO BUG SESSION_KEY")
    print("=" * 60)
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tester = ConversationTester()

    results = []

    # Teste 1: Mensagens consecutivas
    try:
        result = tester.test_consecutive_messages(num_messages=5)
        results.append(("Mensagens Consecutivas", result))
    except Exception as e:
        print(f"\n❌ ERRO no teste: {e}")
        results.append(("Mensagens Consecutivas", False))

    # Teste 2: Direções diferentes
    try:
        result = tester.test_different_directions()
        results.append(("Mensagens Bidirecionais", result))
    except Exception as e:
        print(f"\n❌ ERRO no teste: {e}")
        results.append(("Mensagens Bidirecionais", False))

    # Teste 3: Idempotência
    try:
        result = tester.test_idempotency()
        results.append(("Idempotência", result))
    except Exception as e:
        print(f"\n❌ ERRO no teste: {e}")
        results.append(("Idempotência", False))

    # Resumo
    print(f"\n{'='*60}")
    print("RESUMO DOS TESTES")
    print(f"{'='*60}\n")

    for name, passed in results:
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"{name:30s} {status}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print(f"\n{'='*60}")
    print(f"Total: {passed}/{total} testes passaram")
    print(f"{'='*60}\n")

    # Exit code
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()

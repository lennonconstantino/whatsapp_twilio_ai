# Resumo do Projeto

## Visão Geral
Este projeto é uma plataforma de integração robusta e escalável para automação de conversas no WhatsApp Business via Twilio, potencializada por Inteligência Artificial (LLMs). A solução adota uma arquitetura multi-tenant (SaaS), permitindo que múltiplas organizações gerenciem seus fluxos de conversação de forma isolada e segura.

## Objetivos Principais
- **Automação Inteligente**: Utilização de agentes de IA para gerenciar interações complexas com usuários finais.
- **Escalabilidade Enterprise**: Arquitetura preparada para alto volume de mensagens, com processamento assíncrono distribuído.
- **Segurança e Isolamento**: Modelo de dados multi-tenant estrito, garantindo segregação de dados entre organizações.
- **Resiliência**: Mecanismos avançados de recuperação de falhas, idempotência e consistência eventual.

## Stack Tecnológico Principal
- **Linguagem**: Python 3.12+
- **Framework Web**: FastAPI (Async)
- **Banco de Dados**: PostgreSQL (via Supabase)
- **Fila/Mensageria**: Abstração Agnóstica (Suporte a Redis/BullMQ, SQS, SQLite)
- **Integrações**: Twilio (Canais), OpenAI/LangChain (Inteligência)
- **Infraestrutura**: Docker, Serverless-ready

## Status Atual
O projeto encontra-se em estágio de **"Transição Avançada"** para maturidade Enterprise. O Core da aplicação e a infraestrutura base estão sólidos, implementando padrões como Injeção de Dependência, Strategy para filas e Repositórios Genéricos.

Módulos de negócio críticos (`Identity`, `Conversation`) passaram recentemente por refatorações profundas para eliminar débitos técnicos de MVP, introduzindo:
- Atomicidade via Compensação no registro de usuários.
- Unificação de workers de background.
- Tipagem estrita em serviços de infraestrutura.
- Garantia de idempotência em webhooks.

## Próximos Passos
O foco atual é consolidar a estabilidade dos novos workers unificados e expandir a cobertura de testes para os fluxos de borda (edge cases) da máquina de estados da conversação.

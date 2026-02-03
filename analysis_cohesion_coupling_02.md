# Análise de Acoplamento e Coesão Modular (v2)

Este documento detalha a avaliação de coesão e acoplamento dos módulos do sistema `whatsapp_twilio_ai`, com base na revisão dos relatórios de conformidade e inspeção da estrutura de diretórios.

## 1. Módulo Core (`src/core`)

A fundação de infraestrutura do sistema.

- **Nível de Coesão: ALTO**
  - **Justificativa:** Responsabilidades segregadas rigorosamente por pacotes técnicos (`config`, `database`, `di`, `queue`, `utils`). Cada componente resolve apenas um problema de infraestrutura.
  - **Ponto de Atenção:** O `di/container.py` centraliza a construção de todos os objetos, o que é natural para um container de DI, mas tende a crescer indefinidamente.

- **Nível de Acoplamento: MÉDIO (Aferente Alto / Eferente Baixo)**
  - **Justificativa:**
    - **Aferente (Quem depende dele):** Altíssimo. Todo o sistema depende do Core.
    - **Eferente (De quem ele depende):** Baixo. Depende apenas de bibliotecas externas (Pydantic, SQLAlchemy, etc.).
  - **Risco:** Efeitos colaterais em imports (ex: `load_dotenv` e inicialização de DB global) criam acoplamento implícito e dificultam testes isolados.

## 2. Módulo Conversation (`src/modules/conversation`)

Gerenciamento de estado e histórico de conversas.

- **Nível de Coesão: MÉDIA**
  - **Justificativa:**
    - **Pontos Positivos:** A V2 introduziu componentes especializados (`ConversationFinder`, `ConversationLifecycle`, `ConversationCloser`) em `src/modules/conversation/components/`, melhorando significativamente a coesão da lógica de negócio.
    - **Pontos Negativos:** A coexistência com a API V1 (`api/v1/`) e serviços legados cria uma dualidade. Há lógica de negócio "vazando" para repositórios (ex: validação de transição de estado dentro do repo).
  - **Estrutura Observada:** A separação `api/v1` vs `api/v2` indica uma tentativa de evolução, mas a lógica subjacente ainda compartilha bases que podem estar poluídas.

- **Nível de Acoplamento: ALTO**
  - **Justificativa:**
    - **Infraestrutura:** Componentes de domínio (ex: `ConversationLifecycle`) acessam diretamente tabelas do Supabase para gravar histórico, furando a camada de abstração do repositório.
    - **Dependências:** Fortemente acoplado ao esquema de dados (`owner_id`, `session_key`). Mudanças no banco exigem alterações profundas aqui.

## 3. Módulo AI (`src/modules/ai`)

Motor de inteligência e processamento de linguagem.

- **Nível de Coesão: ALTO**
  - **Justificativa:** Organização clara por *Bounded Contexts* de features (`finance`, `relationships`) dentro de `engines/lchain/feature/`. A lógica de *como* processar (LLM, RAG) está separada da lógica de *o que* processar (regras de negócio das features).
  - **Ponto de Atenção:** Inconsistência nos contratos de `Tools` entre diferentes features.

- **Nível de Acoplamento: MÉDIO**
  - **Justificativa:**
    - Depende do `Identity` para validação de contexto (quem é o usuário), mas isso é feito via interfaces bem definidas.
    - Dependência de RLS (Row Level Security) do banco para isolamento multi-tenant cria um acoplamento implícito com a infraestrutura de dados.

## 4. Módulo Twilio (`src/modules/channels/twilio`)

Adaptador de entrada e saída para WhatsApp.

- **Nível de Coesão: MÉDIA**
  - **Justificativa:** O módulo deveria ser apenas um adaptador (I/O), mas o `TwilioWebhookService` atua como um orquestrador complexo ("God Class"), decidindo fluxos, chamando IA, gerenciando mídia e validando usuários. Isso dilui a responsabilidade principal de "canal".

- **Nível de Acoplamento: MUITO ALTO**
  - **Justificativa:**
    - É o ponto de maior fragilidade arquitetural. Para processar uma mensagem, ele precisa orquestrar `Identity` (quem é), `Conversation` (sessão) e `AI` (resposta).
    - Qualquer mudança nos contratos desses 3 módulos pode quebrar a entrada de mensagens.

## 5. Módulo Identity (`src/modules/identity`)

Gestão de usuários, contas e planos.

- **Nível de Coesão: ALTO**
  - **Justificativa:** Modelagem sólida baseada em agregados (`User`, `Owner`, `Plan`, `Subscription`). Cada sub-domínio tem seus serviços e repositórios.

- **Nível de Acoplamento: MÉDIO**
  - **Justificativa:**
    - **Aferente:** Alto, pois é a fonte de verdade para autorização em todo o sistema.
    - **Interno:** Existem violações de camadas onde serviços acessam repositórios de outros agregados diretamente (ex: `IdentityService` acessando `PlanRepository`), o que aumenta o acoplamento interno do módulo.

---

## Quadro Comparativo

| Módulo | Coesão | Acoplamento | Veredito |
| :--- | :---: | :---: | :--- |
| **Core** | ✅ Alta | ⚠️ Médio | Base sólida, mas cuidado com side-effects. |
| **Conversation**| 🔸 Média | 🔴 Alto | Evolução V2 é boa, mas legado e acoplamento com DB preocupam. |
| **AI** | ✅ Alta | 🟢 Médio | Melhor exemplo de design modular no projeto. |
| **Twilio** | 🔸 Média | 🔴 Muito Alto | Gargalo de manutenção; sabe demais sobre o resto do sistema. |
| **Identity** | ✅ Alta | ⚠️ Médio | Bem estruturado, mas crítico para disponibilidade. |

## Recomendação para `src/modules/conversation`

Dado o foco solicitado neste módulo:
1.  **Consolidar V2:** Priorizar a migração total para a arquitetura de componentes da V2 (`Finder`, `Lifecycle`, `Closer`) e remover rotas/lógica da V1.
2.  **Isolar Infra:** Refatorar `ConversationLifecycle` para não acessar o Supabase diretamente; usar o `ConversationRepository` ou um `HistoryRepository` dedicado.
3.  **Purificar Repositório:** Remover regras de negócio (validação de transição de estado) de dentro do `ConversationRepository` e mantê-las estritamente no `ConversationLifecycle` ou `Service`.

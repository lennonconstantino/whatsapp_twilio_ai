-- ============================================================================
-- CONVERSATION MANAGER - DATABASE SCHEMA
-- ============================================================================
-- Este script cria o schema e as tabelas necessárias para o módulo de 
-- gestão de conversas
-- ============================================================================

-- Criar schema se não existir
CREATE SCHEMA IF NOT EXISTS conversations;

-- Definir o schema como padrão para esta sessão
SET search_path TO conversations;

-- ============================================================================
-- TABELA: conversations
-- ============================================================================
-- Armazena as conversas do sistema
-- ============================================================================

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(20) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    context JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT chk_status CHECK (
        status IN (
            'pending',
            'progress',
            'agent_closed',
            'support_closed',
            'user_closed',
            'expired',
            'failed',
            'idle_timeout'
        )
    )
);

-- Índices para melhorar performance
CREATE INDEX IF NOT EXISTS idx_conversations_phone_number 
    ON conversations(phone_number);

CREATE INDEX IF NOT EXISTS idx_conversations_status 
    ON conversations(status);

CREATE INDEX IF NOT EXISTS idx_conversations_created_at 
    ON conversations(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_conversations_expires_at 
    ON conversations(expires_at) 
    WHERE expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_conversations_phone_status 
    ON conversations(phone_number, status);

-- Índice GIN para busca em JSONB
CREATE INDEX IF NOT EXISTS idx_conversations_metadata 
    ON conversations USING GIN(metadata);

-- ============================================================================
-- TABELA: messages
-- ============================================================================
-- Armazena as mensagens trocadas nas conversas
-- ============================================================================

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    content TEXT NOT NULL DEFAULT '',
    path VARCHAR(500),
    message_owner VARCHAR(20) NOT NULL DEFAULT 'system',
    message_type VARCHAR(20) NOT NULL DEFAULT 'text',
    direction VARCHAR(20) NOT NULL DEFAULT 'inbound',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_message_owner CHECK (
        message_owner IN ('user', 'agent', 'system', 'tool', 'support')
    ),
    CONSTRAINT chk_message_type CHECK (
        message_type IN ('text', 'image', 'audio', 'video', 'document')
    ),
    CONSTRAINT chk_direction CHECK (
        direction IN ('inbound', 'outbound')
    )
);

-- Índices para melhorar performance
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id 
    ON messages(conversation_id);

CREATE INDEX IF NOT EXISTS idx_messages_created_at 
    ON messages(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_messages_message_owner 
    ON messages(message_owner);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_created 
    ON messages(conversation_id, created_at DESC);

-- Índice GIN para busca em JSONB
CREATE INDEX IF NOT EXISTS idx_messages_metadata 
    ON messages USING GIN(metadata);

-- Índice para busca full-text no conteúdo (opcional, útil para pesquisas)
CREATE INDEX IF NOT EXISTS idx_messages_content_search 
    ON messages USING GIN(to_tsvector('portuguese', content));

-- ============================================================================
-- FUNÇÕES E TRIGGERS
-- ============================================================================

-- Função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para atualizar updated_at em conversations
DROP TRIGGER IF EXISTS trigger_conversations_updated_at ON conversations;
CREATE TRIGGER trigger_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- View para conversas ativas
CREATE OR REPLACE VIEW active_conversations AS
SELECT 
    c.*,
    COUNT(m.id) as message_count,
    MAX(m.created_at) as last_message_at
FROM conversations c
LEFT JOIN messages m ON c.id = m.conversation_id
WHERE c.status IN ('pending', 'progress', 'idle_timeout')
GROUP BY c.id;

-- View para conversas expiradas
CREATE OR REPLACE VIEW expired_conversations AS
SELECT 
    c.*,
    COUNT(m.id) as message_count
FROM conversations c
LEFT JOIN messages m ON c.id = m.conversation_id
WHERE c.expires_at IS NOT NULL 
    AND c.expires_at < CURRENT_TIMESTAMP
    AND c.status NOT IN ('expired', 'agent_closed', 'support_closed', 'user_closed', 'failed')
GROUP BY c.id;

-- View para estatísticas de conversas
CREATE OR REPLACE VIEW conversation_statistics AS
SELECT 
    status,
    COUNT(*) as total,
    DATE_TRUNC('day', created_at) as date
FROM conversations
GROUP BY status, DATE_TRUNC('day', created_at)
ORDER BY date DESC, status;

-- ============================================================================
-- PERMISSÕES (ajustar conforme necessário)
-- ============================================================================

-- Garantir que o schema tenha as permissões corretas
GRANT USAGE ON SCHEMA conversations TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA conversations TO PUBLIC;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA conversations TO PUBLIC;

-- ============================================================================
-- COMENTÁRIOS
-- ============================================================================

COMMENT ON SCHEMA conversations IS 'Schema para gestão de conversas e mensagens';
COMMENT ON TABLE conversations IS 'Armazena informações das conversas';
COMMENT ON TABLE messages IS 'Armazena mensagens trocadas nas conversas';
COMMENT ON COLUMN conversations.context IS 'Contexto da conversa em formato JSONB';
COMMENT ON COLUMN conversations.metadata IS 'Metadados adicionais como canal, dispositivo, etc';
COMMENT ON COLUMN messages.metadata IS 'Metadados da mensagem incluindo eventos de canal';

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================

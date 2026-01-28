-- ==============================================
-- Migração de Tabelas para Feature Relationships
-- ==============================================

-- ==============================================
-- Tabela: person
-- ==============================================
CREATE TABLE IF NOT EXISTS person (
    id BIGSERIAL PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    tags TEXT,
    birthday DATE,
    city TEXT,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_person_name ON person(last_name, first_name);
CREATE INDEX IF NOT EXISTS idx_person_phone ON person(phone);
CREATE INDEX IF NOT EXISTS idx_person_tags ON person(tags);

-- Trigger para atualizar updated_at automaticamente
CREATE TRIGGER update_person_updated_at
    BEFORE UPDATE ON person
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ==============================================
-- Tabela: interaction
-- ==============================================
CREATE TABLE IF NOT EXISTS interaction (
    id BIGSERIAL PRIMARY KEY,
    person_id BIGINT REFERENCES person(id) ON DELETE CASCADE,
    date TIMESTAMP WITH TIME ZONE NOT NULL,
    channel TEXT NOT NULL,
    type TEXT NOT NULL,
    summary TEXT,
    sentiment NUMERIC(3, 2), -- Ex: 0.85
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_interaction_person_id ON interaction(person_id);
CREATE INDEX IF NOT EXISTS idx_interaction_date ON interaction(date);

-- Trigger para atualizar updated_at automaticamente
CREATE TRIGGER update_interaction_updated_at
    BEFORE UPDATE ON interaction
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ==============================================
-- Tabela: reminder
-- ==============================================
CREATE TABLE IF NOT EXISTS reminder (
    id BIGSERIAL PRIMARY KEY,
    person_id BIGINT REFERENCES person(id) ON DELETE CASCADE,
    due_date TIMESTAMP WITH TIME ZONE NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_reminder_person_id ON reminder(person_id);
CREATE INDEX IF NOT EXISTS idx_reminder_due_date ON reminder(due_date);
CREATE INDEX IF NOT EXISTS idx_reminder_status ON reminder(status);

-- Trigger para atualizar updated_at automaticamente
DROP TRIGGER IF EXISTS update_reminder_updated_at ON reminder;
CREATE TRIGGER update_reminder_updated_at
    BEFORE UPDATE ON reminder
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==============================================
-- Comentários nas tabelas
-- ==============================================
COMMENT ON TABLE person IS 'Tabela de contatos/pessoas do CRM de relacionamentos';
COMMENT ON TABLE interaction IS 'Histórico de interações com as pessoas';
COMMENT ON TABLE reminder IS 'Lembretes e tarefas relacionadas às pessoas';

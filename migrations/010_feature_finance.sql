-- ==============================================
-- Migração de Tabelas para Supabase
-- ==============================================
-- Execute este SQL no SQL Editor do Supabase
-- ou via Supabase CLI

-- Habilitar extensões úteis (opcional)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- DROP VIEWS
-- ============================================================================
DROP VIEW IF EXISTS monthly_financial_summary CASCADE;
DROP VIEW IF EXISTS invoice_details CASCADE;

-- ==============================================
-- Tabela: revenue
-- ==============================================
CREATE TABLE IF NOT EXISTS revenue (
    id BIGSERIAL PRIMARY KEY,
    description TEXT NOT NULL,
    net_amount NUMERIC(12, 2) NOT NULL,
    gross_amount NUMERIC(12, 2) NOT NULL,
    tax_rate NUMERIC(5, 4) NOT NULL,
    date TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_revenue_date ON revenue(date);
CREATE INDEX IF NOT EXISTS idx_revenue_created_at ON revenue(created_at);

-- Trigger para atualizar updated_at automaticamente
-- NOTA: A função update_updated_at_column() já foi criada em 002_create_core_functions.sql

CREATE TRIGGER update_revenue_updated_at
    BEFORE UPDATE ON revenue
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ==============================================
-- Tabela: expense
-- ==============================================
CREATE TABLE IF NOT EXISTS expense (
    id BIGSERIAL PRIMARY KEY,
    description TEXT NOT NULL,
    net_amount NUMERIC(12, 2) NOT NULL,
    gross_amount NUMERIC(12, 2) NOT NULL,
    tax_rate NUMERIC(5, 4) NOT NULL,
    date TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_expense_date ON expense(date);
CREATE INDEX IF NOT EXISTS idx_expense_created_at ON expense(created_at);

-- Trigger para atualizar updated_at automaticamente
CREATE TRIGGER update_expense_updated_at
    BEFORE UPDATE ON expense
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ==============================================
-- Tabela: customer
-- ==============================================
CREATE TABLE IF NOT EXISTS customer (
    id BIGSERIAL PRIMARY KEY,
    company_name TEXT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    city TEXT NOT NULL,
    zip TEXT NOT NULL,
    country TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_customer_name ON customer(last_name, first_name);
CREATE INDEX IF NOT EXISTS idx_customer_phone ON customer(phone);
CREATE INDEX IF NOT EXISTS idx_customer_company ON customer(company_name);

-- Trigger para atualizar updated_at automaticamente
CREATE TRIGGER update_customer_updated_at
    BEFORE UPDATE ON customer
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ==============================================
-- Tabela: invoice
-- ==============================================
CREATE TABLE IF NOT EXISTS invoice (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT REFERENCES customer(id) ON DELETE SET NULL,
    invoice_number TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    tax_rate NUMERIC(5, 4) NOT NULL,
    date TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_invoice_customer_id ON invoice(customer_id);
CREATE INDEX IF NOT EXISTS idx_invoice_number ON invoice(invoice_number);
CREATE INDEX IF NOT EXISTS idx_invoice_date ON invoice(date);

-- Trigger para atualizar updated_at automaticamente
CREATE TRIGGER update_invoice_updated_at
    BEFORE UPDATE ON invoice
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ==============================================
-- Políticas RLS (Row Level Security) - Opcional
-- ==============================================
-- Descomente e ajuste conforme suas necessidades de segurança

-- Habilitar RLS
-- ALTER TABLE revenue ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE expense ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE customer ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE invoice ENABLE ROW LEVEL SECURITY;

-- Exemplo: Política que permite acesso apenas a dados do próprio usuário
-- Você precisará adicionar uma coluna user_id nas tabelas

-- CREATE POLICY "Users can view their own revenue"
--     ON revenue FOR SELECT
--     USING (auth.uid() = user_id);

-- CREATE POLICY "Users can insert their own revenue"
--     ON revenue FOR INSERT
--     WITH CHECK (auth.uid() = user_id);

-- CREATE POLICY "Users can update their own revenue"
--     ON revenue FOR UPDATE
--     USING (auth.uid() = user_id);

-- CREATE POLICY "Users can delete their own revenue"
--     ON revenue FOR DELETE
--     USING (auth.uid() = user_id);

-- Repita para as outras tabelas...


-- ==============================================
-- Dados de Exemplo (Seed Data) - Opcional
-- ==============================================
-- Descomente para inserir dados de teste

-- INSERT INTO customer (company_name, first_name, last_name, phone, address, city, zip, country) VALUES
-- ('Tech Corp', 'John', 'Doe', '+1234567890', '123 Main St', 'New York', '10001', 'USA'),
-- ('Design Ltd', 'Jane', 'Smith', '+0987654321', '456 Oak Ave', 'Los Angeles', '90001', 'USA'),
-- (NULL, 'Bob', 'Johnson', '+1122334455', '789 Pine Rd', 'Chicago', '60601', 'USA');

-- INSERT INTO revenue (description, net_amount, gross_amount, tax_rate, date) VALUES
-- ('Consulting services', 1000.00, 1190.00, 0.19, '2024-01-15 10:00:00'),
-- ('Software license', 500.00, 595.00, 0.19, '2024-02-20 14:30:00'),
-- ('Training workshop', 1500.00, 1785.00, 0.19, '2024-03-10 09:00:00');

-- INSERT INTO expense (description, net_amount, gross_amount, tax_rate, date) VALUES
-- ('Office supplies', 100.00, 119.00, 0.19, '2024-01-10 08:00:00'),
-- ('Software subscription', 50.00, 59.50, 0.19, '2024-02-05 12:00:00'),
-- ('Marketing campaign', 300.00, 357.00, 0.19, '2024-03-15 16:00:00');

-- INSERT INTO invoice (customer_id, invoice_number, description, amount, tax_rate, date) VALUES
-- (1, 'INV-1001', 'Website development', 1500.00, 0.19, '2024-01-20 10:00:00'),
-- (2, 'INV-1002', 'Project completion', 2380.00, 0.19, '2024-02-15 11:00:00'),
-- (3, 'INV-1003', 'Software license', 595.00, 0.19, '2024-03-10 15:00:00');


-- ==============================================
-- Views úteis (Opcional)
-- ==============================================

-- View para resumo financeiro mensal
CREATE OR REPLACE VIEW monthly_financial_summary AS
SELECT 
    DATE_TRUNC('month', date) AS month,
    'revenue' AS type,
    SUM(gross_amount) AS total_amount,
    COUNT(*) AS transaction_count
FROM revenue
GROUP BY DATE_TRUNC('month', date)
UNION ALL
SELECT 
    DATE_TRUNC('month', date) AS month,
    'expense' AS type,
    SUM(gross_amount) AS total_amount,
    COUNT(*) AS transaction_count
FROM expense
GROUP BY DATE_TRUNC('month', date)
ORDER BY month DESC, type;

-- View para invoices com informações do cliente
CREATE OR REPLACE VIEW invoice_details AS
SELECT 
    i.id,
    i.invoice_number,
    i.description,
    i.amount,
    i.tax_rate,
    i.date,
    c.company_name,
    c.first_name,
    c.last_name,
    c.phone,
    c.city,
    c.country
FROM invoice i
LEFT JOIN customer c ON i.customer_id = c.id;


-- ==============================================
-- Comentários nas tabelas (Documentação)
-- ==============================================

COMMENT ON TABLE revenue IS 'Tabela de receitas da empresa';
COMMENT ON TABLE expense IS 'Tabela de despesas da empresa';
COMMENT ON TABLE customer IS 'Tabela de clientes';
COMMENT ON TABLE invoice IS 'Tabela de faturas emitidas';

COMMENT ON COLUMN revenue.net_amount IS 'Valor líquido (antes dos impostos)';
COMMENT ON COLUMN revenue.gross_amount IS 'Valor bruto (com impostos)';
COMMENT ON COLUMN revenue.tax_rate IS 'Taxa de imposto aplicada (ex: 0.19 para 19%)';

COMMENT ON COLUMN expense.net_amount IS 'Valor líquido da despesa (antes dos impostos)';
COMMENT ON COLUMN expense.gross_amount IS 'Valor bruto da despesa (com impostos)';
COMMENT ON COLUMN expense.tax_rate IS 'Taxa de imposto aplicada (ex: 0.19 para 19%)';

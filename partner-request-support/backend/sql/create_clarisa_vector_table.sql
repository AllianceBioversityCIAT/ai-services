-- ============================================================
-- Tabla vectorial para instituciones de CLARISA
-- ============================================================
-- Esta tabla almacena los datos directos de la API de CLARISA
-- con embeddings separados para nombre y acrónimo para búsqueda
-- híbrida con similitud coseno + RapidFuzz

-- Habilitar la extensión de vectores si no está habilitada
CREATE EXTENSION IF NOT EXISTS vector;

-- Crear la tabla principal de instituciones CLARISA
CREATE TABLE IF NOT EXISTS clarisa_institutions_v2 (
    id SERIAL PRIMARY KEY,
    clarisa_id INTEGER UNIQUE NOT NULL,  -- El 'code' de la API de CLARISA
    name TEXT NOT NULL,
    acronym TEXT,
    website TEXT,
    countries TEXT[],  -- Array de nombres de países
    institution_type TEXT,
    name_embedding vector(1024),  -- Embedding del nombre (Titan v2 = 1024 dims)
    acronym_embedding vector(1024),  -- Embedding del acrónimo
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para mejorar rendimiento
CREATE INDEX IF NOT EXISTS idx_clarisa_institutions_v2_clarisa_id 
    ON clarisa_institutions_v2(clarisa_id);

CREATE INDEX IF NOT EXISTS idx_clarisa_institutions_v2_name 
    ON clarisa_institutions_v2(name);

CREATE INDEX IF NOT EXISTS idx_clarisa_institutions_v2_acronym 
    ON clarisa_institutions_v2(acronym);

-- Índices vectoriales para búsqueda por similitud
-- ivfflat es eficiente para datasets grandes
CREATE INDEX IF NOT EXISTS idx_clarisa_institutions_v2_name_embedding 
    ON clarisa_institutions_v2 
    USING ivfflat (name_embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_clarisa_institutions_v2_acronym_embedding 
    ON clarisa_institutions_v2 
    USING ivfflat (acronym_embedding vector_cosine_ops)
    WITH (lists = 100);

-- Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para updated_at
DROP TRIGGER IF EXISTS update_clarisa_institutions_v2_updated_at 
    ON clarisa_institutions_v2;
    
CREATE TRIGGER update_clarisa_institutions_v2_updated_at
    BEFORE UPDATE ON clarisa_institutions_v2
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- Función RPC para búsqueda híbrida por nombre
-- ============================================================
-- Retorna los top 5 matches más similares usando similitud coseno

CREATE OR REPLACE FUNCTION search_institution_by_name(
    query_embedding vector(1024),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    clarisa_id INTEGER,
    name TEXT,
    acronym TEXT,
    website TEXT,
    countries TEXT[],
    institution_type TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ci.clarisa_id,
        ci.name,
        ci.acronym,
        ci.website,
        ci.countries,
        ci.institution_type,
        1 - (ci.name_embedding <=> query_embedding) AS similarity
    FROM clarisa_institutions_v2 ci
    WHERE ci.name_embedding IS NOT NULL
        AND 1 - (ci.name_embedding <=> query_embedding) > match_threshold
    ORDER BY ci.name_embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================================
-- Función RPC para búsqueda híbrida por acrónimo
-- ============================================================

CREATE OR REPLACE FUNCTION search_institution_by_acronym(
    query_embedding vector(1024),
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    clarisa_id INTEGER,
    name TEXT,
    acronym TEXT,
    website TEXT,
    countries TEXT[],
    institution_type TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ci.clarisa_id,
        ci.name,
        ci.acronym,
        ci.website,
        ci.countries,
        ci.institution_type,
        1 - (ci.acronym_embedding <=> query_embedding) AS similarity
    FROM clarisa_institutions_v2 ci
    WHERE ci.acronym_embedding IS NOT NULL
        AND 1 - (ci.acronym_embedding <=> query_embedding) > match_threshold
    ORDER BY ci.acronym_embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================================
-- Función RPC para búsqueda combinada (nombre + acrónimo)
-- ============================================================
-- Combina ambos scores con pesos configurables

CREATE OR REPLACE FUNCTION search_institution_combined(
    name_query_embedding vector(1024),
    acronym_query_embedding vector(1024),
    name_weight float DEFAULT 0.7,
    acronym_weight float DEFAULT 0.3,
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    clarisa_id INTEGER,
    name TEXT,
    acronym TEXT,
    website TEXT,
    countries TEXT[],
    institution_type TEXT,
    combined_similarity FLOAT,
    name_similarity FLOAT,
    acronym_similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ci.clarisa_id,
        ci.name,
        ci.acronym,
        ci.website,
        ci.countries,
        ci.institution_type,
        (
            COALESCE(1 - (ci.name_embedding <=> name_query_embedding), 0) * name_weight +
            COALESCE(1 - (ci.acronym_embedding <=> acronym_query_embedding), 0) * acronym_weight
        ) AS combined_similarity,
        (1 - (ci.name_embedding <=> name_query_embedding)) AS name_similarity,
        (1 - (ci.acronym_embedding <=> acronym_query_embedding)) AS acronym_similarity
    FROM clarisa_institutions_v2 ci
    WHERE 
        (ci.name_embedding IS NOT NULL OR ci.acronym_embedding IS NOT NULL)
        AND (
            COALESCE(1 - (ci.name_embedding <=> name_query_embedding), 0) * name_weight +
            COALESCE(1 - (ci.acronym_embedding <=> acronym_query_embedding), 0) * acronym_weight
        ) > match_threshold
    ORDER BY combined_similarity DESC
    LIMIT match_count;
END;
$$;

-- Comentarios sobre la tabla
COMMENT ON TABLE clarisa_institutions_v2 IS 'Instituciones de CLARISA con embeddings vectoriales para búsqueda híbrida';
COMMENT ON COLUMN clarisa_institutions_v2.clarisa_id IS 'ID único de la institución en CLARISA (code de la API)';
COMMENT ON COLUMN clarisa_institutions_v2.name_embedding IS 'Vector de embedding del nombre (1024 dims, Amazon Titan v2)';
COMMENT ON COLUMN clarisa_institutions_v2.acronym_embedding IS 'Vector de embedding del acrónimo (1024 dims, Amazon Titan v2)';
COMMENT ON COLUMN clarisa_institutions_v2.countries IS 'Array de nombres de países donde la institución tiene oficinas';

DO $$BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'theme') THEN
        CREATE TABLE theme (
            id UUID PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            summary TEXT,
            url VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'article') THEN
        CREATE TABLE article (
            id UUID PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            content TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    END IF;
END$$;

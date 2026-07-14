CREATE TABLE IF NOT EXISTS aihelms.license (
    id INTEGER PRIMARY KEY DEFAULT 1,
    licensed_to TEXT,
    features JSONB NOT NULL DEFAULT '[]',
    issued_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    license_key TEXT,
    status TEXT NOT NULL DEFAULT 'invalid',
    imported_at TIMESTAMPTZ,
    CONSTRAINT license_singleton CHECK (id = 1)
);

CREATE TABLE IF NOT EXISTS aihelms.branding (
    id INTEGER PRIMARY KEY DEFAULT 1,
    platform_name TEXT NOT NULL DEFAULT 'AIHelms',
    logo_path TEXT,
    favicon_path TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT branding_singleton CHECK (id = 1)
);

INSERT INTO aihelms.branding (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE demand_title (
    title_id      BIGINT IDENTITY PRIMARY KEY,
    title         VARCHAR(200) NOT NULL,
    market        VARCHAR(10)  NOT NULL,
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE demand_signal (
    signal_id     BIGINT IDENTITY PRIMARY KEY,
    title_id      BIGINT       NOT NULL REFERENCES demand_title(title_id),
    kind          VARCHAR(40)  NOT NULL,
    observed_at   DATE         NOT NULL,
    value         DECIMAL(18,4) NOT NULL,
    source_url    VARCHAR(500) NOT NULL,
    weight        DECIMAL(5,2) NOT NULL DEFAULT 1.0,
    UNIQUE (title_id, kind, observed_at, source_url)
);

CREATE TABLE demand_evidence (
    evidence_id   BIGINT IDENTITY PRIMARY KEY,
    title_id      BIGINT       NOT NULL REFERENCES demand_title(title_id),
    kind          VARCHAR(40)  NOT NULL,
    source_url    VARCHAR(500) NOT NULL,
    quote         VARCHAR(2000) NOT NULL
);

CREATE TABLE demand_assessment (
    assessment_id UUID PRIMARY KEY,
    title_id      BIGINT       NOT NULL REFERENCES demand_title(title_id),
    momentum      DECIMAL(10,4) NOT NULL,
    confidence    DECIMAL(5,4) NOT NULL,
    status        VARCHAR(20)  NOT NULL,
    flags_json    VARCHAR(2000) NOT NULL,
    explanation   VARCHAR(4000) NOT NULL,
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_signal_title_kind ON demand_signal(title_id, kind, observed_at);
CREATE INDEX ix_assessment_status ON demand_assessment(status, created_at);

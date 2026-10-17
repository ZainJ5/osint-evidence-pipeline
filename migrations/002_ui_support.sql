-- 002: fields the web UI shows. Rows written before this migration read back as "no solved count" / "no matches".

ALTER TABLE claims ADD COLUMN solved INTEGER NULL;  -- problems claimed, for kind 'solved'

ALTER TABLE score_reports ADD COLUMN matches JSONB NOT NULL DEFAULT '[]';  -- per required skill (SkillMatch)

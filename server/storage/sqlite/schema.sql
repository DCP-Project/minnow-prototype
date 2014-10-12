CREATE TABLE IF NOT EXISTS 'user' (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(48) UNIQUE NOT NULL,
    password VARCHAR(128) NOT NULL,
    gecos VARCHAR(64),
    timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    avatar BLOB -- XXX does this belong here?
);

CREATE TABLE IF NOT EXISTS 'acl_user' (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    acl VARCHAR(32) NOT NULL,
    user_id INTEGER NOT NULL,
    setter_id INTEGER,
    timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    reason TEXT,
    FOREIGN KEY(user_id) REFERENCES 'user(id)' ON DELETE CASCADE ON UPDATE
        CASCADE,
    FOREIGN KEY(setter_id) REFERENCES 'user(id)' ON DELETE SET NULL ON UPDATE
        CASCADE,
    UNIQUE(acl, user_id)
);

CREATE TABLE IF NOT EXISTS 'property_user' (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property VARCHAR(32) NOT NULL,
    value VARCHAR(32),
    user_id INTEGER NOT NULL,
    setter_id INTEGER,
    timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY(user_id) REFERENCES 'user(id)' ON DELETE CASCADE ON UPDATE
        CASCADE,
    FOREIGN KEY(setter_id) REFERENCES 'user(id)' ON DELETE SET NULL ON UPDATE
        CASCADE,
    UNIQUE(property, user_id)
);

CREATE TABLE IF NOT EXISTS 'group' (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(48) UNIQUE NOT NULL,
    topic TEXT,
    timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE IF NOT EXISTS 'acl_group' (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    acl VARCHAR(32) NOT NULL,
    user_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,
    setter_id INTEGER,
    timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    reason TEXT,
    FOREIGN KEY(user_id) REFERENCES 'user(id)' ON DELETE CASCADE ON UPDATE
        CASCADE,
    FOREIGN KEY(group_id) REFERENCES 'group(id)' ON DELETE CASCADE ON UPDATE
        CASCADE,
    FOREIGN KEY(setter_id) REFERENCES 'user(id)' ON DELETE SET NULL ON UPDATE
        CASCADE,
    UNIQUE(acl, user_id, group_id)
);

CREATE TABLE IF NOT EXISTS 'property_group' (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property VARCHAR(32) NOT NULL,
    value VARCHAR(32),
    group_id INTEGER NOT NULL,
    setter_id INTEGER,
    timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY(group_id) REFERENCES 'group(id)' ON DELETE CASCADE ON UPDATE
        CASCADE,
    FOREIGN KEY(setter_id) REFERENCES 'user(id)' ON DELETE SET NULL ON
        UPDATE CASCADE,
    UNIQUE(property, group_id)
);

CREATE TABLE IF NOT EXISTS 'roster' (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    FOREIGN KEY(user_id) REFERENCES 'user(id)' ON DELETE CASCADE ON UPDATE
        CASCADE,
    UNIQUE(user_id)
);

CREATE TABLE IF NOT EXISTS 'roster_entry_user' (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL, -- Stores the member, NOT the owner of the entry!
    roster_id INTEGER NOT NULL,
    alias VARCHAR(512),
    group_tag VARCHAR(32),
    blocked INTEGER DEFAULT (0),
    pending INTEGER DEFAULT (0),
    FOREIGN KEY(user_id) REFERENCES 'user(id)' ON DELETE CASCADE ON UPDATE
        CASCADE,
    FOREIGN KEY(roster_id) REFERENCES 'roster(id)' ON DELETE CASCADE ON UPDATE
        CASCADE,
    UNIQUE(user_id, roster_id)
);

CREATE TABLE IF NOT EXISTS 'roster_entry_group' (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    roster_id INTEGER NOT NULL,
    alias VARCHAR(512),
    group_tag VARCHAR(32),
    FOREIGN KEY(group_id) REFERENCES 'group(id)' ON DELETE CASCADE ON UPDATE
        CASCADE,
    FOREIGN KEY(roster_id) REFERENCES 'roster(id)' ON DELETE CASCADE ON UPDATE
        CASCADE,
    UNIQUE(group_id, roster_id)
);

CREATE TRIGGER IF NOT EXISTS "user_create_trigger" AFTER INSERT ON "user"
BEGIN
    INSERT INTO "roster" (user_id) VALUES (NEW.user_id);
END;

-- Ugh I botched updates. :(
DROP TABLE IF EXISTS 'version';

CREATE TABLE IF NOT EXISTS 'version' (
    id INTEGER PRIMARY KEY ON CONFLICT IGNORE,
    version INTEGER UNIQUE DEFAULT (2)
);

INSERT OR IGNORE INTO 'version' VALUES (0, 2);

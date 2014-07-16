CREATE TABLE IF NOT EXISTS 'user' (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(48) UNIQUE NOT NULL,
    password VARCHAR(128) NOT NULL,
    gecos VARCHAR(64),
    timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE IF NOT EXISTS 'acl_user' (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    acl VARCHAR(32) NOT NULL,
    user_id INTEGER NOT NULL,
    setter_id INTEGER,
    timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY(user_id) REFERENCES 'user(id)' ON DELETE CASCADE ON UPDATE
        CASCADE,
    FOREIGN KEY(setter_id) REFERENCES 'user(id)' ON DELETE SET NULL ON UPDATE
        CASCADE,
    UNIQUE(acl, user_id)
);

CREATE TABLE IF NOT EXISTS 'config_user' (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config VARCHAR(32) NOT NULL,
    value VARCHAR(32),
    user_id INTEGER NOT NULL,
    setter_id INTEGER,
    timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY(user_id) REFERENCES 'user(id)' ON DELETE CASCADE ON UPDATE
        CASCADE,
    FOREIGN KEY(setter_id) REFERENCES 'user(id)' ON DELETE SET NULL ON UPDATE
        CASCADE,
    UNIQUE(config, user_id)
);

CREATE TABLE IF NOT EXISTS 'group' (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(48) UNIQUE NOT NULL,
    timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE IF NOT EXISTS 'acl_group' (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    acl VARCHAR(32) NOT NULL,
    user_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,
    setter_id INTEGER,
    timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY(user_id) REFERENCES 'user(id)' ON DELETE CASCADE ON UPDATE
        CASCADE,
    FOREIGN KEY(group_id) REFERENCES 'group(id)' ON DELETE CASCADE ON UPDATE
        CASCADE,
    FOREIGN KEY(setter_id) REFERENCES 'user(id)' ON DELETE SET NULL ON UPDATE
        CASCADE,
    UNIQUE(acl, user_id, group_id)
);

CREATE TABLE IF NOT EXISTS 'config_group' (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config VARCHAR(32) NOT NULL,
    value VARCHAR(32),
    group_id INTEGER NOT NULL,
    setter_id INTEGER,
    timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY(group_id) REFERENCES 'group(id)' ON DELETE CASCADE ON UPDATE
        CASCADE,
    FOREIGN KEY(setter_id) REFERENCES 'user(id)' ON DELETE SET NULL ON
        UPDATE CASCADE,
    UNIQUE(config, group_id)
);

CREATE TABLE IF NOT EXISTS 'version' (
    id INTEGER UNIQUE NOT NULL
);

INSERT OR REPLACE INTO 'version' VALUES (1);

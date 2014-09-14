s_get_user = 'SELECT "user".* FROM "user" WHERE "name"=?'

s_get_user_acl = 'SELECT "acl_user".acl,"acl_user".timestamp,"user2".name ' \
    'FROM "acl_user","user" LEFT OUTER JOIN user AS user2 ON ' \
    '"acl_user".setter_id="user2".id WHERE "user".name=? AND ' \
    '"acl_user".user_id="user".id '

s_get_user_property = 'SELECT "property_user".* FROM "property_user",' \
    '"user" WHERE "user".name=? AND "property_user".user_id="user".id'

s_get_group = 'SELECT "group".* FROM "group" WHERE "name"=?'

s_get_group_acl = 'SELECT "acl_group".acl,"acl_group".timestamp,"user".name ' \
    'FROM "acl_group","group" LEFT OUTER JOIN "user" ' \
    'ON "acl_group".user_id="user".id WHERE "group".name=?'

s_get_group_acl_user = 'SELECT "acl_group".*,"user2".name FROM ' \
    '"acl_group","user" LEFT OUTER JOIN "user" as "user2" ON ' \
    '"acl_user".setter_id="user2".id WHERE "group".name=? AND ' \
    '"user".name=? AND "group".id="acl_group".group_id AND ' \
    '"user".id="acl_user".user_id'

s_get_group_property = 'SELECT "property_group".*,"user".name AS username ' \
    'FROM "property_group","user","group" WHERE "group".name=? AND ' \
    '"group".id="property_group".group_id AND ' \
    '"user".id="property_group".user_id'

s_create_user = 'INSERT INTO "user" (name,gecos,password) VALUES (?,?,?)'

s_create_group = 'INSERT INTO "group" (name,topic) VALUES(?,?)'

s_create_user_acl = 'INSERT INTO "acl_user" (acl,user_id,reason) VALUES(' \
    '(SELECT ?,"user".id FROM "user" WHERE "user".name=?), ?)'

s_create_group_acl = 'INSERT INTO "acl_group" (acl,group_id,user_id,' \
    'setter_id,reason) VALUES((SELECT ?),(SELECT "group".id FROM "group" ' \
    'WHERE "group".name=?),(SELECT "user".id FROM "user" WHERE ' \
    '"user".name=?), (SELECT "user".id FROM "user" WHERE "user".name=?), ?)'

s_set_user = 'UPDATE "user" SET gecos=IFNULL(?,gecos),password=' \
    'IFNULL(?,password) WHERE "user".name=?'

s_set_group = 'UPDATE "group" SET topic=? WHERE "group".name=?'

s_set_property_user = 'INSERT OR REPLACE INTO "property_user" (property,' \
    'value,user_id,setter_id) VALUES((SELECT ?),(SELECT ?),(SELECT ' \
    '"user".id FROM "user" WHERE "user".name=?))'

s_set_property_group = 'INSERT OR REPLACE INTO "property_group" (property,' \
    'value,group_id,setter_id) VALUES((SELECT ?),(SELECT ?),(SELECT ' \
    '"group".id FROM "group" WHERE "group".name=?),(SELECT "user".id FROM ' \
    '"user" WHERE "user".name=?))'

s_del_user = 'DELETE FROM "user" WHERE "user".name=?'

s_del_user_acl = 'DELETE FROM "acl_user" WHERE "acl_user".acl=? AND ' \
    '"acl_user".user_id IN (SELECT "user".id FROM "user" WHERE "user".name=?)'

s_del_user_acl_all = 'DELETE FROM "acl_user" WHERE "acl_user".user_id IN ' \
    '(SELECT "user".id FROM "user" WHERE "user".name=?)'

s_del_group_acl = 'DELETE FROM "acl_group" WHERE "acl_group".acl=? AND ' \
    '"acl_group".user_id IN (SELECT "user".id FROM "user" WHERE ' \
    '"user".name=?) AND "acl_group".group_id IN (SELECT "group".id FROM ' \
    '"group" WHERE "group".name=?)'

s_del_group_acl_all = 'DELETE FROM "acl_group" WHERE "acl_group".group_id ' \
    'IN (SELECT "group".id FROM "group" WHERE "group".name=?)'

s_del_group = 'DELETE FROM "group" WHERE "group".name=?'

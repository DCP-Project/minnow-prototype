# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

# Retrieval
s_get_user = 'SELECT "user".password,"user".gecos,"user".timestamp,' \
    '"user".avatar FROM "user" WHERE "user".name=? ORDER BY "user".name'

s_get_user_acl = 'SELECT "acl_user".acl,"acl_user".timestamp,"setter".name ' \
    'AS setter FROM "acl_user","user" LEFT OUTER JOIN "user" AS "setter" ' \
    'ON "acl_user".setter_id="user2".id WHERE "user".name=? AND ' \
    '"acl_user".user_id="user".id ORDER BY "acl_user".acl'

s_get_user_property = 'SELECT "property_user".property,' \
    '"property_user".value,"property_user".timestamp,"user2".name AS ' \
    'setter FROM "property_user","user" LEFT OUTER JOIN "user" AS "user2" ' \
    'ON "property_user".setter_id="user2".id WHERE "user".name=? AND ' \
    '"property_user".user_id="user".id ORDER BY "property_user".property'

s_get_roster_user = 'SELECT "roster_entry_user".alias,' \
    '"roster_entry_user".group_tag,"roster_entry_user".blocked,' \
    '"target".name FROM "roster","roster_entry_user","user","user" AS ' \
    '"target" WHERE "user".name=? AND "roster".user_id="user".id AND ' \
    '"roster".id="roster_entry_user".roster_id AND "target".id=' \
    '"roster_entry_user".user_id ORDER BY "target".name'

s_get_group = 'SELECT "group".topic,"group".timestamp FROM "group" WHERE ' \
    '"name"=?'

s_get_group_acl = 'SELECT "acl_group".acl,"acl_group".timestamp,' \
    '"acl_group".reason,"target".name AS target,"setter".name AS setter ' \
    'FROM "acl_group","group","user" AS "target" LEFT OUTER JOIN "user" AS ' \
    '"setter" ON "acl_group".setter_id="setter".id WHERE "group".name=? ' \
    'AND "acl_group".user_id="target".id'

s_get_group_acl_user = 'SELECT "acl_group".acl,"acl_group".timestamp",' \
    '"acl_group".reason,"setter".name AS setter FROM "acl_group","user" ' \
    'LEFT OUTER JOIN "user" as "setter" ON "acl_user".setter_id="user2".id ' \
    'WHERE "group".name=? AND "user".name=? AND "group".id=' \
    '"acl_group".group_id AND "user".id="acl_user".user_id ORDER BY ' \
    '"acl_group".acl'

s_get_group_property = 'SELECT "property_group".property,' \
    '"property_group".value,"property_user".timestamp,"user".name AS ' \
    'setter FROM "property_group","group" LEFT OUTER JOIN "user" ON ' \
    '"property_user".setter_id="user2".id WHERE "group".name=? AND ' \
    '"group".id="property_group".group_id ORDER BY "property_group".property'

s_get_roster_group = 'SELECT "roster_entry_group".alias,' \
    '"roster_entry_group".group_tag,"group".name FROM "roster",' \
    '"roster_entry_group","user","group" WHERE "user".name=? AND ' \
    '"roster".user_id="user".id AND "roster".id=' \
    '"roster_entry_group".roster_id AND "group".id=' \
    '"roster_entry_group".group_id ORDER BY "group".name'

# Creation
s_create_user = 'INSERT INTO "user" (name,gecos,password) VALUES (?,?,?)'

s_create_group = 'INSERT INTO "group" (name,topic) VALUES(?,?)'

s_create_user_acl = 'INSERT INTO "acl_user" (acl,user_id,reason) VALUES(' \
    '(SELECT ?,"user".id FROM "user" WHERE "user".name=?),?)'

s_create_group_acl = 'INSERT INTO "acl_group" (acl,group_id,user_id,' \
    'setter_id,reason) VALUES(?,(SELECT "group".id FROM "group" WHERE ' \
    '"group".name=?),(SELECT "user".id FROM "user" WHERE "user".name=?),' \
    '(SELECT "user".id FROM "user" WHERE "user".name=?),?)'

s_create_property_user = 'INSERT INTO "property_user" (property,value,' \
    'user_id,setter_id) VALUES(?,?,(SELECT "user".id FROM "user" WHERE ' \
    '"user".name=?),(SELECT "user".id FROM "user" WHERE "user".name=?))'

s_create_property_group = 'INSERT INTO "property_group" (property,value,' \
    'group_id,setter_id) VALUES(?,?,(SELECT "group".id FROM "group" WHERE ' \
    '"group".name=?),(SELECT "user".id FROM "user" WHERE "user".name=?))'

s_create_roster_user = 'INSERT INTO "roster_entry_user" (roster_id,user_id,' \
    'alias,group_tag) VALUES((SELECT "roster".id FROM "roster","user" ' \
    'WHERE "user".name=? AND "roster".user_id="user".id),(SELECT ' \
    '"user".id FROM "user" WHERE "user".name=?),?,?)'

s_create_roster_group = 'INSERT INTO "roster_entry_group" (roster_id,' \
    'group_id,alias,group_tag) VALUES((SELECT "roster".roster_id FROM ' \
    '"roster","user" WHERE "user".name=? AND "roster".user_id="user".id),' \
    '(SELECT "group".id FROM "group" WHERE "group".name=?)'

# Alteration
s_set_user = 'UPDATE "user" SET gecos=IFNULL(?,gecos),password=' \
    'IFNULL(?,password) WHERE "user".name=?'

s_set_group = 'UPDATE "group" SET topic=? WHERE "group".name=?'

s_set_property_user = 'UPDATE "property_user" SET value=? WHERE ' \
    '"property_user".property=? AND "property_user".user_id=(SELECT ' \
    '"user".id FROM "user" WHERE "user".name=?)'

s_set_property_group = 'UPDATE "property_group" SET value=? WHERE ' \
    '"property_group".property=? AND "property_group".group_id=(SELECT ' \
    '"group".id FROM "group" WHERE "group".name=?)'

s_set_roster_user = 'UPDATE "roster_entry_user" SET alias=IFNULL(?,alias),' \
    'group_tag=IFNULL(?,group_tag),blocked=IFNULL(?,blocked) WHERE ' \
    '"roster_entry_user".roster_id=(SELECT "user".id FROM "user" WHERE ' \
    '"user".name=?)'

s_set_roster_group = 'UPDATE "roster_entry_group" SET alias=IFNULL(?,alias),' \
    'group_tag=IFNULL(?,group_tag) WHERE "roster_entry_group".roster_id=' \
    '(SELECT "user".id FROM "user" WHERE "user".name=?)'

# Deletion
s_del_user = 'DELETE FROM "user" WHERE "user".name=?'

s_del_user_acl = 'DELETE FROM "acl_user" WHERE "acl_user".acl=? AND ' \
    '"acl_user".user_id = (SELECT "user".id FROM "user" WHERE "user".name=?)'

s_del_user_acl_all = 'DELETE FROM "acl_user" WHERE "acl_user".user_id IN ' \
    '(SELECT "user".id FROM "user" WHERE "user".name=?)'

s_del_group_acl = 'DELETE FROM "acl_group" WHERE "acl_group".acl=? AND ' \
    '"acl_group".user_id = (SELECT "user".id FROM "user" WHERE ' \
    '"user".name=?) AND "acl_group".group_id = (SELECT "group".id FROM ' \
    '"group" WHERE "group".name=?)'

s_del_group_acl_all = 'DELETE FROM "acl_group" WHERE "acl_group".group_id =' \
    '(SELECT "group".id FROM "group" WHERE "group".name=?)'

s_del_group = 'DELETE FROM "group" WHERE "group".name=?'

s_del_property_user = 'DELETE FROM "property_user" WHERE ' \
    '"property_user".property=? AND "property_user".user_id=(SELECT ' \
    '"user".id FROM "user" WHERE "user".name=?)'

s_del_property_group = 'DELETE FROM "property_group" WHERE ' \
    '"property_group".property=? AND "property_group".group_id=(SELECT ' \
    '"group".id FROM "group" WHERE "group".name=?)'

s_del_roster_user = 'DELETE FROM "roster_entry_user" WHERE ' \
    '"roster_entry_user".roster_id=(SELECT "roster".id FROM "roster",' \
    '"user" WHERE "user".name=? AND "user".id="roster".user_id) AND ' \
    '"roster_entry_user".user_id=(SELECT "user".id FROM "user" WHERE ' \
    '"user".name=?)'

s_del_roster_group = 'DELETE FROM "roster_entry_group" WHERE ' \
    '"roster_entry_group".roster_id=(SELECT "roster".id FROM "roster",' \
    '"user" WHERE "user".name=? AND "user".id="roster".user_id) AND ' \
    '"roster_entry_group".group_id=(SELECT "group".id FROM "group" WHERE ' \
    '"group".name=?)'

# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

class Entity:
    """The base entity class - servers, users, and groups 
    
    If it has ACL's, properties, and metadata, it's an entity.
    """

    def __init__(self, name, acl, property, metadata):
        self.name = name
        self.acl = acl
        self.property = property
        self.metadata = metadata

    # TODO - persistence stuff will go here

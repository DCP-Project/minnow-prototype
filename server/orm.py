# coding: utf-8

from pprint import pprint

from sqlalchemy.engine import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, sessionmaker
from sqlalchemy.schema import Column, ForeignKey, UniqueConstraint
from sqlalchemy.sql.functions import now
from sqlalchemy.sql.expression import insert, select
from sqlalchemy.types import (LargeBinary, Integer, Unicode, UnicodeText,
                              DateTime, Boolean)


Base = declarative_base()


def check_name_casefold(context):
    return context.current_parameters['name'].casefold()


class Entity(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True)

    name = Column(Unicode(48), nullable=False)
    name_casefold = Column(
        Unicode(96),
        unique=True,
        default=check_name_casefold,
        onupdate=check_name_casefold)

    timestamp = Column(DateTime, server_default=now(), nullable=False)


class User(Entity):
    __tablename__ = 'user'

    password = Column(Unicode(128), nullable=False)
    gecos = Column(Unicode(1024))
    avatar = Column(LargeBinary)

    roster = relationship(
        'Roster',
        backref=backref(
            'user',
            cascade='all',
            lazy='joined',
            innerjoin=True),
        cascade='all,delete-orphan',
        uselist=False,
        lazy='joined',
        passive_deletes=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.roster = Roster(user=self)

    def __repr__(self):
        return 'User(name={}, password={}, gecos={}, timestamp={}, ' \
            '<avatar_size={}>)'.format(
                self.name,
                self.password,
                self.gecos,
                self.timestamp,
                (len(self.avatar) if self.avatar else 0))


class Group(Entity):
    __tablename__ = 'group'

    topic = Column(UnicodeText)

    def __repr__(self):
        return 'Group(name={}, topic={}, timestamp={})'.format(
            self.name,
            self.topic,
            self.timestamp)

class ACL(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True)

    acl = Column(Unicode(32), nullable=False)

    user_id = Column(
        Integer,
        ForeignKey(
            'user.id',
            ondelete='CASCADE',
            onupdate='CASCADE'))

    setter_id = Column(
        Integer,
        ForeignKey(
            'user.id',
            ondelete='SET NULL',
            onupdate='CASCADE'))
    setter = relationship('User', foreign_keys=[setter_id])

    timestamp = Column(DateTime, server_default=now(), nullable=False)
    reason = Column(UnicodeText)


class ACLUser(ACL):
    __tablename__ = 'acl_user'

    user = relationship(
        'User',
        backref=backref(
            'acls',
            cascade='all,delete-orphan',
            lazy='joined',
            passive_deletes=True),
        lazy='joined',
        innerjoin=True,
        foreign_keys=[user_id])

    __table_args__ = (UniqueConstraint('acl', 'user_id'),)

    def __repr__(self):
        return 'ACLUser(acl={}, user={}, setter={}, timestamp={}, ' \
            'reason={})'.format(
                self.acl,
                self.user,
                self.setter,
                self.timestamp,
                self.reason)


class ACLGroup(ACL):
    __tablename__ = 'acl_group'

    user = relationship(
        'User',
        backref=backref(
            'acl_group',
            cascade='all,delete-orphan',
            passive_deletes=True),
        cascade='all',
        foreign_keys=[user_id])

    group_id = Column(
        Integer,
        ForeignKey(
            'group.id',
            ondelete='CASCADE',
            onupdate='CASCADE'),
        nullable=False)
    group = relationship(
        'Group',
        backref=backref(
            'acls',
            cascade='all,delete-orphan',
            lazy='joined',
            passive_deletes=True),
        cascade='all',
        lazy='joined',
        innerjoin=True,
        foreign_keys=[group_id])

    __table_args__ = (UniqueConstraint('acl', 'user_id', 'group_id'),)

    def __repr__(self):
        return 'ACLGroup(acl={}, user={}, setter={}, group={}, ' \
            'timestamp={}, reason={})'.format(
                self.acl,
                self.user,
                self.setter,
                self.group,
                self.timestamp,
                self.reason)


class Property(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True)

    property = Column(Unicode(32), nullable=False)
    value = Column(Unicode(32))

    user_id = Column(
        Integer,
        ForeignKey(
            'user.id',
            ondelete='CASCADE',
            onupdate='CASCADE'),
        nullable=False)

    setter_id = Column(
        Integer,
        ForeignKey(
            'user.id',
            ondelete='SET NULL',
            onupdate='CASCADE'))
    setter = relationship('User', foreign_keys=[setter_id])

    timestamp = Column(DateTime, server_default=now(), nullable=False)


class PropertyUser(Property):
    __tablename__ = 'property_user'

    user = relationship(
        'User',
        backref=backref(
            'properties',
            cascade='all,delete-orphan',
            lazy='joined',
            passive_deletes=True),
        cascade='all',
        lazy='joined',
        innerjoin=True,
        foreign_keys=[user_id])

    __table_args__ = (UniqueConstraint('property', 'user_id'),)

    def __repr__(self):
        return 'PropertyUser(property={}, value={}, user={}, setter={}, ' \
            'timestamp={})'.format(
                self.property,
                self.value,
                self.user,
                self.setter,
                self.timestamp)


class PropertyGroup(Property):
    __tablename__ = 'property_group'

    user = relationship('User', cascade='all', foreign_keys=[user_id])

    group_id = Column(
        Integer,
        ForeignKey(
            'group.id',
            ondelete='CASCADE',
            onupdate='CASCADE'),
        nullable=False)
    group = relationship(
        'Group',
        backref=backref(
            'properties',
            cascade='all,delete-orphan',
            lazy='joined',
            passive_deletes=True),
        cascade='all',
        foreign_keys=[group_id])

    __table_args__ = (UniqueConstraint('property', 'user_id', 'group_id'),)

    def __repr__(self):
        return 'PropertyGroup(property={}, value={}, user={}, setter={}, ' \
            'group={}, timestamp={})'.format(
                self.property,
                self.value,
                self.user,
                self.setter,
                self.group,
                self.timestamp)


class Roster(Base):
    __tablename__ = 'roster'
    id = Column(Integer, primary_key=True)

    user_id = Column(
        'user_id',
        Integer,
        ForeignKey(
            'user.id',
            ondelete='CASCADE',
            onupdate='CASCADE'),
        unique=True,
        nullable=False)

    def __repr__(self):
        return 'Roster(user={}, <user entries={}>, <group entries={}>'.format(
            self.user,
            len(self.user_roster),
            len(self.group_roster))


class RosterEntry(AbstractConcrete

class RosterEntryUser(Base):
    __tablename__ = 'roster_entry_user'
    id = Column(Integer, primary_key=True)

    roster_id = Column(
        Integer,
        ForeignKey(
            'roster.id',
            ondelete='CASCADE',
            onupdate='CASCADE'),
        nullable=False)
    roster = relationship(
        'Roster',
        backref=backref(
            'user_roster',
            cascade='all,delete-orphan',
            lazy='joined',
            innerjoin=True,
            passive_deletes=True),
        cascade='all',
        lazy='joined',
        innerjoin=True)

    user_id = Column(
        Integer,
        ForeignKey(
            'user.id',
            ondelete='CASCADE',
            onupdate='CASCADE'),
        nullable=False)
    user = relationship('User', cascade='all')

    alias = Column(Unicode(1024))
    group_tag = Column(Unicode(1024))
    blocked = Column(Boolean, default=False)
    pending = Column(Boolean, default=True)
    __table_args__ = (UniqueConstraint('user_id', 'roster_id'),)

    def __repr__(self):
        return 'RosterEntryUser(roster={}, user={}, alias={}, ' \
            'group_tag={}, blocked={}, pending={})'.format(
                self.roster,
                self.user,
                self.alias,
                self.group_tag,
                self.blocked,
                self.pending)


class RosterEntryGroup(Base):
    __tablename__ = 'roster_entry_group'
    id = Column(Integer, primary_key=True)

    roster_id = Column(
        Integer,
        ForeignKey(
            'roster.id',
            ondelete='CASCADE',
            onupdate='CASCADE'),
        nullable=False)
    roster = relationship('Roster', backref='group_roster', cascade='all')

    group_id = Column(
        Integer,
        ForeignKey(
            'group.id',
            ondelete='CASCADE',
            onupdate='CASCADE'),
        nullable=False)
    group = relationship('Group', cascade='all')

    alias = Column(Unicode(1024))
    group_tag = Column(Unicode(64))
    __table_args__ = (UniqueConstraint('group_id', 'roster_id'),)

    def __repr__(self):
        return 'RosterEntryGroup(roster={}, group={}, alias={}, ' \
            'group_tag={})'.format(
                self.roster,
                self.group,
                self.alias,
                self.group_tag)


engine = create_engine('sqlite:///:memory:', echo=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

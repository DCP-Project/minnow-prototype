# coding=utf-8
# Copyright © 2014 Elizabeth Myers, Andrew Wilcox. All rights reserved.
# This software is free and open source. You can redistribute and/or modify it
# under the terms of the Do What The Fuck You Want To Public License, Version
# 2, as published by Sam Hocevar. See the LICENSE file for more details.

from datastructure import CaselessDict

# Defined metadata types that we have built-in for reference
user_metadata = {
    'status', 'status-message', 'now-playing-artist', 'now-playing-track',
    'now-playing-album', 'now-playing-time', 'now-playing-genre',
    'now-playing-mediaplayer', 'contact-irc', 'contact-aim', 'contact-xmpp',
    'contact-skype', 'contact-email', 'contact-facebook', 'contact-google+',
    'contact-twitter', 'contact-github', 'contact-bitbucket',
    'contact-google-code', 'contact-phone', 'contact-sms', 'contact-address',
    'url'}

group_metadata = {
    'topic', 'about', 'url', 'rules', 'contact-irc', 'contact-facebook',
    'contact-twitter', 'contact-google+', 'contact-skype',
    'contact-mailing-list', 'contact-github', 'contact-bitbucket',
    'contact-google-code'}

class MetadataStorage(CaselessDict):
    pass

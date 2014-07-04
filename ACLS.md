# Minnow ACLs

## Introduction
Here are a list of ACL's supported by minnow and what they do

## User ACL's
| ACL             | Function                                                        |
|-----------------|-----------------------------------------------------------------|
| user:auspex     | Inspect user information (can see channels in whois, etc.)      |
| user:register   | Can register users (if registrations are restricted)            |
| user:revoke     | Can revoke a user registration                                  |
| user:grant      | Can grant user ACL's (only ACL's that they possess themselves)  |
| user:disconnect | Can force disconnect users (a 'kill' in IRC parlance)           |
| user:ban        | Can ban IP addresses, usernames, and accounts from the server   |

## Group ACL's
| ACL             | Function                                                        |
|-----------------|-----------------------------------------------------------------|
| group:auspex    | Inspect group information without being present (even when the  |
|                 | group is private)                                               |
| group:register  | Can create groups (if registrations are restricted)             |
| group:override  | Can override group properties                                   |
| group:revoke    | Can revoke a group, clearing it from the server                 |
| group:ban       | Can ban a specific group from being created                     |

# What happened to LOS?
It was going great for a while along with the frequent updates recieved, right? Well when you don't have any time management skills, it all goes down hill and because it went down hill I just never decided to touch it again.

# Whats going to be new in v2?
New design, new mindset, new me, new everything. The same features from v1 will be included, but the code base and idea of the project will be completely different.

# Design of V2
```mermaid
flowchart TB
USER(user)
USER_SYSTEM(user's system)
APPLICATION(application)
OSU_CLIENT(osu! client)
BANCHO_SERVICE{bancho service}
WEB_SERVICE{web service}
AVATAR_SERVICE{avatar service}
CONTROL_POINT{control service}
SCORE_SUBMISSION_SERVICE{score-submission daemon}
DOMAIN((domain))
CLOUD_FLARE((cloudflare))

%% =================================
USER -.-> USER_SYSTEM

USER --> APPLICATION --> CONTROL_POINT
USER_SYSTEM --> SCORE_SUBMISSION_SERVICE

USER --> OSU_CLIENT --> DOMAIN --> CLOUD_FLARE  --> CONTROL_POINT

CONTROL_POINT --> BANCHO_SERVICE
CONTROL_POINT --> WEB_SERVICE
CONTROL_POINT --> AVATAR_SERVICE
```

# Directory Structure
```mermaid
flowchart LR
coming_soon
```

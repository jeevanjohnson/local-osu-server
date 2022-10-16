# What happened to LOS?
It was going great for a while along with the frequent updates recieved, right? Well when you don't have any time management skills, it all goes down hill and because it went down hill I just never decided to touch it again.

# Whats going to be new in v2?
New design, new mindset, new me, new everything. The same features from v1 will be included, but the code base and idea of the project will be completely different.

# Design of V2
```Mermaid
flowchart LR
USER(user)
APPLICATION(application)
OSU_CLIENT(osu! client)
PARSING_SERVICE{parsing service} 
BANCHO_SERVICE{bancho service}
WEB_SERVICE{web service}
AVATAR_SERVICE{avatar service}
CONTROL_POINT{control service}
SCORE_SUBMISSION_SERVICE{score-submission service}
DOMAIN((domain))
CLOUD_FLARE((cloud flare))

%% =================================
USER --> APPLICATION --> CONTROL_POINT

USER --> OSU_CLIENT --> DOMAIN --> CLOUD_FLARE --> PARSING_SERVICE --> CONTROL_POINT

CONTROL_POINT --> BANCHO_SERVICE
CONTROL_POINT --> WEB_SERVICE
CONTROL_POINT --> AVATAR_SERVICE
CONTROL_POINT --> SCORE_SUBMISSION_SERVICE
```

# Directory Structure
```Mermaid
flowchart LR
coming_soon
```
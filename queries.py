from typing import Union

def init_profile(name: str) -> dict[str, Union[int, list[str], dict]]:
    return {
        name: {
            'pp': 0,
            'acc': 0,
            'playcount': 0,
            'plays': {
                'ranked_plays': {},
                'loved_plays': {},
                'qualified_plays': {},
                'approved_plays': {},
                'all_plays': [],
                'replay_md5': []
            }
        }
    }
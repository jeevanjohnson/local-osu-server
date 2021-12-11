from typing import Union

# TODO: proper typing?
def init_profile(name: str) -> dict[str, Union[int, list, dict]]:
    return {
        name: {
            'pp': 0,
            'acc': 0,
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
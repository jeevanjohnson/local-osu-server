from typing import Optional, Union


def get_profile_name_from_args(args: dict[str, str]) -> Optional[str]:
    return args.get("profile_name")


def parse_body_args(raw_body: Union[str, bytes]) -> dict[str, str]:
    if isinstance(raw_body, bytes):
        raw_args = raw_body.decode()
    else:
        raw_args = raw_body

    args = {}

    for arg in raw_args.split("&"):
        key, value = arg.split("=", 1)

        args[key] = value

    return args

import webbrowser

from adapters import log, log_time

# TODO: use the osu! client update protocol for our server updates :3


@log_time
def open_lazer_score(score_id: int) -> None:
    success = webbrowser.open_new_tab(f"https://osu.ppy.sh/scores/{score_id}")

    if not success:
        log.error(f"Failed to open web browser for score id {score_id}")
    else:
        log.success(f"Opened web browser for score id {score_id}")

    return None

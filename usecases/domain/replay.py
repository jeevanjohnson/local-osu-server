import webbrowser

# from adapters import log, log_time


# log
def open_lazer_score(score_id: int) -> None:
    success = webbrowser.open_new_tab(f"https://osu.ppy.sh/scores/{score_id}")

    if not success:
        print(f"Failed to open web browser for score id {score_id}")
    else:
        print(f"Opened web browser for score id {score_id}")

    return None

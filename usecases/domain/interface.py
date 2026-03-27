"""
Purpose/Domain/Concept:
- This file contains the logic for handling/checking GUI-related operations.
"""

from repositories.client.state import ClientStateRepository


async def logged_in() -> bool:
    client_state_repo = ClientStateRepository()
    # profile_repo = ProfilesRepository()

    client_state = await client_state_repo.get_client_state()

    if not client_state.logged_in:
        return False

    return True

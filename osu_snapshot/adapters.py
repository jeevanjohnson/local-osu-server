from jays_tools.architecture import Adapter
import aiohttp

class OsuWebsiteAdapter(Adapter):
    
    async def get_home_page(self) -> str:
        async with aiohttp.ClientSession() as http:
            async with http.get("https://osu.ppy.sh/") as response:
                
                if response.status != 200:
                    print(f"Failed to fetch total registered users, status code: {response.status}")
                    raise Exception("Failed to fetch home page")

                return await response.text()    

    async def get_ranking_page(self, page: int, game_mode: str) -> str:
        if game_mode not in ["osu", "taiko", "fruits", "mania"]:
            raise ValueError(f"Invalid game mode: {game_mode}. Must be one of 'osu', 'taiko', 'fruits', 'mania'.")
    
        if page < 1:
            raise ValueError(f"Invalid page number: {page}. Page number must be greater than or equal to 1.")

        if page > 200:
            raise ValueError(f"Invalid page number: {page}. Page number must be less than or equal to 200.")

        url = f"https://osu.ppy.sh/rankings/{game_mode}/global/performance?filter=all&page={page}#scores"
        
        async with aiohttp.ClientSession() as http:
            async with http.get(url) as response:
                
                if response.status != 200:
                    print(f"Failed to fetch page {page} for mode {game_mode}, status code: {response.status}")
                    raise Exception(f"Failed to fetch ranking page for mode {game_mode} and page {page}")

                return await response.text()
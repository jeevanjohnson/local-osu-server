from jays_tools.architecture import Service
from bs4 import BeautifulSoup
from scipy.optimize import curve_fit
import numpy as np

PP = int
RANK = int

class OsuScraperService(Service):

    def get_total_registered_users(self, home_page_html: str) -> int:
        soup = BeautifulSoup(home_page_html, "html.parser")
        
        div = soup.find("div", class_="landing-hero__info")
        
        if div is None:
            raise ValueError("Could not find the div with class 'landing-hero__info'")
        
        registered_users = div.find("strong")
        if registered_users is None:
            raise ValueError("Could not find the strong element with registered users count")
        
        return int(registered_users.get_text(strip=True).replace(",", ""))
    
    def extract_pp_and_ranks(self, ranking_page_html: str) -> list[tuple[PP, RANK]]:
        soup = BeautifulSoup(ranking_page_html, "html.parser")
        
        rank_rows = soup.find_all("tr", class_="ranking-page-table__row")

        pp_and_ranks = []

        for row in rank_rows:
            row_str = row.get_text(strip=True, separator="|")

            row_list = row_str.split("|")

            # get 4th to last element
            pp_str = row_list[-4]
            rank_str = row_list[0]

            pp = int(pp_str.replace(",", "").strip())
            rank = int(rank_str.replace("#", "").replace(",", "").strip())
            pp_and_ranks.append((pp, rank))

        return pp_and_ranks

class OsuEstimatorService(Service):
    
    def generate_synthetic_pp_and_ranks(
        self, known_pp_and_ranks: list[tuple[PP, RANK]], 
        total_users: RANK
    ) -> list[tuple[PP, RANK]]:
        # anchor points for curve fitting
        # osu! std in specific but should be okay for other modes
        known_pp_and_ranks.extend([
            (1858, 539_495),
            (611, 1_196_844),
        ])

        known_pp_and_ranks.sort(key=lambda x: x[1]) # Sort by rank (ascending)

        pps = np.array([rank[0] for rank in known_pp_and_ranks], dtype=float)
        ranks = np.array([rank[1] for rank in known_pp_and_ranks], dtype=float)

        # Fit in log space: log(pp) = log(a) + b*rank
        def log_exponential_model(rank, log_a, b):
            return log_a + b * rank

        popt, _ = curve_fit(log_exponential_model, ranks, np.log(pps))
        log_a_fitted, b_fitted = popt

        last_rank = ranks[-1]

        synthetic_pp_rank_pairs = []

        current_rank = last_rank
        while current_rank < total_users:
            current_rank = int(current_rank * 1.5)
            if current_rank >= total_users:
                current_rank = total_users
        
            # Convert back from log space: pp = e^(log_a + b*rank)
            current_pp = int(np.exp(log_a_fitted + b_fitted * current_rank))
            current_pp = max(0, current_pp)

            if current_pp > 0:
                synthetic_pp_rank_pairs.append((current_pp, current_rank))

        synthetic_pp_rank_pairs.append((0, total_users))  # Add the total users with 0 pp at the end

        return synthetic_pp_rank_pairs
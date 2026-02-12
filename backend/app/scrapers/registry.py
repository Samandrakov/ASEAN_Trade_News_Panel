from .base import BaseScraper
from .indonesia.antara import AntaraScraper
from .indonesia.jakarta_post import JakartaPostScraper
from .indonesia.kompas import KompasScraper
from .malaysia.bernama import BernamaScraper
from .malaysia.malaymail import MalayMailScraper
from .malaysia.thestar import TheStarScraper
from .vietnam.tuoitre import TuoiTreScraper
from .vietnam.vietnam_news import VietnamNewsScraper
from .vietnam.vnexpress import VnExpressScraper

SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "jakarta_post": JakartaPostScraper,
    "kompas": KompasScraper,
    "antara": AntaraScraper,
    "vnexpress": VnExpressScraper,
    "vietnam_news": VietnamNewsScraper,
    "tuoitre": TuoiTreScraper,
    "thestar": TheStarScraper,
    "malaymail": MalayMailScraper,
    "bernama": BernamaScraper,
}

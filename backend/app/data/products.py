"""Client product catalog — Italian names with English aliases."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogProduct:
    name_it: str
    aliases: tuple[str, ...] = ()
    default_form: str = "unknown"  # fresh, frozen, unknown


PRODUCT_CATALOG: list[CatalogProduct] = [
    CatalogProduct("gambero rosso", ("red shrimp", "red deep sea prawn rosso", "gambero rosso"), "frozen"),
    CatalogProduct("gambero viola", ("purple shrimp", "red deep sea prawn viola", "gambero viola"), "frozen"),
    CatalogProduct("polpa di riccio", ("sea urchin", "sea urchin roe", "riccio"), "frozen"),
    CatalogProduct("ombrina", ("meagre", "corvina"), "fresh"),
    CatalogProduct("orata", ("sea bream", "spigola"), "fresh"),
    CatalogProduct("branzino", ("sea bass",), "fresh"),
    CatalogProduct("trota", ("trout",), "fresh"),
    CatalogProduct("trota salmonata", ("salmon trout", "rainbow trout"), "frozen"),
    CatalogProduct("sgombro", ("mackerel",), "fresh"),
    CatalogProduct("latterini", ("latterini",), "fresh"),
    CatalogProduct("vongole veraci", ("clams", "vongole", "decussatus", "phillipinarum", "manila clam"), "fresh"),
    CatalogProduct("tellina", ("tellina",), "fresh"),
    CatalogProduct("moscardino", ("moscardino",), "fresh"),
    CatalogProduct("piatti pronti", ("rtc", "ready to cook", "ready meals", "piatti pronti"), "frozen"),
    CatalogProduct("sogliola", ("sole",), "fresh"),
    CatalogProduct("seppia", ("cuttlefish",), "fresh"),
    CatalogProduct("polpo", ("octopus",), "fresh"),
    CatalogProduct("atherina", ("atherina",), "frozen"),
]

FRESH_KEYWORDS = (
    "fresco", "fresca", "freschi", "fresche", "fresh",
    "vivo", "viva", "vivi", "intero", "intera", "eviscerat",
    "sottovuoto", "ivp", "al vivo",
)

FROZEN_KEYWORDS = (
    "congelat", "frozen", "surgelat", "iqf", "gelo",
    "frozen ", " fros",
)

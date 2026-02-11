#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Crawl XtraWine product pages (wines) from a seed URL list, extract a structured JSON per wine,
and save to NDJSON (streaming) + final JSON array.

Usage:
  python crawl_xtrawine.py --max 100 --out xtrawine_wines.json --delay 1.2 --jitter 0.8
"""

from __future__ import annotations

import argparse
import json
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, urlunparse, ParseResult

import requests
from bs4 import BeautifulSoup


# ---------------------------
# Config / seeds
# ---------------------------

SEED_WINE_URLS: List[str] = [
    "https://www.xtrawine.com/en-nl/products/ceci-otello-nero-di-lambrusco",
    "https://www.xtrawine.com/en-nl/products/montalbera-metodo-classico-120-1-pas-dose",
    "https://www.xtrawine.com/en-nl/products/monte-rossa-franciacorta-cabochon-millesimato-brut-2016",
    "https://www.xtrawine.com/en-nl/products/monte-rossa-franciacorta-cabochon-doppiozero-brut-nature-2018",
    "https://www.xtrawine.com/en-nl/products/monte-zovo-chiaretto-di-bardolino-phasianus-2021",
    "https://www.xtrawine.com/en-nl/products/montresor-amarone-della-valpolicella-cantina-privata-del-fondatore-2019",
    "https://www.xtrawine.com/en-nl/products/moratti-oltrepo-pavese-pas-dose-millesimato-metodo-classico-cuvee-dellangelo-2015",
    "https://www.xtrawine.com/en-nl/products/mottura-salice-salentino-le-pitre-2021",
    "https://www.xtrawine.com/en-nl/products/mutiliana-pinot-nero-forli-ecce-drago-2022",
    "https://www.xtrawine.com/en-nl/products/mutiliana-romagna-sangiovese-modigliana-tramazo-2021",
    "https://www.xtrawine.com/en-nl/products/marchesi-migliorati-cerasuolo-dabruzzo-2023",
    "https://www.xtrawine.com/en-nl/products/mastroberardino-taurasi-stilema-riserva-2016",
    "https://www.xtrawine.com/en-nl/products/domini-veneti-amarone-della-valpolicella-classico-collezione-pruviniano-2020",
    "https://www.xtrawine.com/en-nl/products/domini-veneti-recioto-della-valpolicella-sentate-spumante-dolce-2022",
    "https://www.xtrawine.com/en-nl/products/domini-veneti-valpolicella-classico-2023",
    "https://www.xtrawine.com/en-nl/products/domini-veneti-valpolicella-classico-superiore-2022",
    "https://www.xtrawine.com/en-nl/products/domini-veneti-recioto-della-valpolicella-classico-0-375l-2020",
    "https://www.xtrawine.com/en-nl/products/nestore-bosco-1897-pecorino-2023",
    "https://www.xtrawine.com/en-nl/products/niedrist-ignaz-mitterberg-weiss-trias-2020",
    "https://www.xtrawine.com/en-nl/products/castello-di-monsanto-fabrizio-bianchi-sangioveto-grosso-2018",
    "https://www.xtrawine.com/en-nl/products/poggio-argentiera-syrah-podereadua-2021",
    "https://www.xtrawine.com/en-nl/products/bodega-delgado-zuleta-vermut-goyesco-0-75-l",
    "https://www.xtrawine.com/en-nl/products/mastrojanni-ciliegiolo-2020",
    "https://www.xtrawine.com/en-nl/products/andre-beaufort-champagne-polisy-brut-2005",
    "https://www.xtrawine.com/en-nl/products/domaine-guy-bocard-meursault-charmes-1er-cru-2020",
    "https://www.xtrawine.com/en-nl/products/domaine-guy-bocard-bourgonge-aligote-les-chanterelles-2022",
    "https://www.xtrawine.com/en-nl/products/domaine-guy-bocard-meursault-les-narvaux-2020",
    "https://www.xtrawine.com/en-nl/products/de-fermo-cerasuolo-dabruzzo-le-cince-2023",
    "https://www.xtrawine.com/en-nl/products/moser-trento-51-151-brut-magnum",
    "https://www.xtrawine.com/en-nl/products/col-vetoraz-brut-rosa-12-lune-2022",
    "https://www.xtrawine.com/en-nl/products/oenosaphiens-revolution-malbec-2023",
    "https://www.xtrawine.com/en-nl/products/la-rasina-brunello-di-montalcino-2019",
    "https://www.xtrawine.com/en-nl/products/joseph-pascal-puligny-montrachet-2022",
    "https://www.xtrawine.com/en-nl/products/nicosia-sosta-tre-santi-etna-brut-metodo-classico-millesimato-2020",
    "https://www.xtrawine.com/en-nl/products/nicosia-vegan-grillo-2023",
    "https://www.xtrawine.com/en-nl/products/nicosia-monte-gorna-etna-rosso-vecchie-viti-riserva-2017",
    "https://www.xtrawine.com/en-nl/products/nicosia-sosta-tre-santi-carricante-brut-metodo-classico-millesimato-2020",
    "https://www.xtrawine.com/en-nl/products/priorat-humilitat-2019",
    "https://www.xtrawine.com/en-nl/products/oenosaphiens-samurai-chenin-blanc-2023",
    "https://www.xtrawine.com/en-nl/products/umberto-cesari-moma-bianco-2023",
    "https://www.xtrawine.com/en-nl/products/andre-beaufort-champagne-ambonnay-grand-cru-reserve-brut-nature",
    "https://www.xtrawine.com/en-nl/products/oddero-barolo-villero-2020",
    "https://www.xtrawine.com/en-nl/products/ampeleia-rosato-2022",
    "https://www.xtrawine.com/en-nl/products/moser-trento-riserva-tracce-extra-brut-2011",
    "https://www.xtrawine.com/en-nl/products/oenosaphiens-cotes-du-jura-poolsard-2023",
    "https://www.xtrawine.com/en-nl/products/henri-boillot-puligny-montrachet-1er-cru-les-folatieres-2020",
    "https://www.xtrawine.com/en-nl/products/henri-boillot-puligny-montrachet-1er-cru-clos-de-la-mouchere-monopole-2022",
    "https://www.xtrawine.com/en-nl/products/suavia-soave-classico-castellaro-2020",
    "https://www.xtrawine.com/en-nl/products/suavia-soave-classico-fitta-2020",
    "https://www.xtrawine.com/en-nl/products/suavia-soave-classico-tremenalto-2020",
    "https://www.xtrawine.com/en-nl/products/domaine-arcelain-bourgogne-rose-2023",
    "https://www.xtrawine.com/en-nl/products/villa-diamante-fiano-di-avellino-clos-dhaut-2022",
    "https://www.xtrawine.com/en-nl/products/jean-gagnerot-gevrey-chambertin-2021",
    "https://www.xtrawine.com/en-nl/products/castello-di-fonterutoli-concerto-di-fonterutoli-2021",
    "https://www.xtrawine.com/en-nl/products/nicolas-feuillatte-champagne-millesime-brut-2015",
    "https://www.xtrawine.com/en-nl/products/feudo-disisa-chardonnay-2021",
    "https://www.xtrawine.com/en-nl/products/palazzone-orvieto-classico-superiore-campo-guardiano-2021",
    "https://www.xtrawine.com/en-nl/products/jermann-vintage-tunina-2022",
    "https://www.xtrawine.com/en-nl/products/jermann-vintage-tunina-magnum-2022",
    "https://www.xtrawine.com/en-nl/products/tenuta-bastonaca-cerasuolo-di-vittoria-classico-2020",
    "https://www.xtrawine.com/en-nl/products/coppo-clelia-metodo-classico-rose-brut-2021",
    "https://www.xtrawine.com/en-nl/products/jean-marc-vincent-santenay-rouge-1er-cru-le-passetemps-2021",
    "https://www.xtrawine.com/en-nl/products/da-vinci-vinsanto-dellempolese-0-5l-2012",
    "https://www.xtrawine.com/en-nl/products/clos-st-antonin-cotes-du-rhone-rouge-2022",
    "https://www.xtrawine.com/en-nl/products/mastrojanni-santantimo-costa-colonne-2022",
    "https://www.xtrawine.com/en-nl/products/banfi-alta-langa-cuvee-aurora-extra-brut-2020",
    "https://www.xtrawine.com/en-nl/products/delouvin-nowack-champagne-les-chaillets-loupette-blanc-de-noirs-brut-nature",
    "https://www.xtrawine.com/en-nl/products/joseph-pascal-bourgogne-cote-dor-pinot-noir-2022",
    "https://www.xtrawine.com/en-nl/products/tenuta-masseria-setteporte-etna-rosato-nerello-in-rosa-2023",
    "https://www.xtrawine.com/en-nl/products/foradori-granato-magnum-2021",
    "https://www.xtrawine.com/en-nl/products/alois-lageder-cabernet-sauvignon-cor-romigberg-2019",
    "https://www.xtrawine.com/en-nl/products/damilano-barolo-raviole-2020",
    "https://www.xtrawine.com/en-nl/products/damilano-barolo-cannubi-2020",
    "https://www.xtrawine.com/en-nl/products/joseph-drouhin-domaine-des-hospices-de-belleville-brouilly-2021",
    "https://www.xtrawine.com/en-nl/products/j-hofstatter-kolbenhof-gewurztraminer-2022",
    "https://www.xtrawine.com/en-nl/products/david-leclapart-champagne-1er-cru-blanc-de-blancs-lartiste-pas-dose",
    "https://www.xtrawine.com/en-nl/products/domaine-nowack-champagne-tuillerie-extra-brut-2019",
    "https://www.xtrawine.com/en-nl/products/jacques-rousseaux-champagne-grand-cru-noir-de-vigne-extra-brut",
    "https://www.xtrawine.com/en-nl/products/j-charpentier-champagne-extra-brut-millesime-2018",
    "https://www.xtrawine.com/en-nl/products/emilien-feneuil-champagne-1er-cru-blanc-de-blancs-cuvee-totum-extra-brut-2019",
    "https://www.xtrawine.com/en-nl/products/braida-barbera-dasti-montebruna-2021",
    "https://www.xtrawine.com/en-nl/products/tornatore-etna-rosso-contrada-trimarchisa-2018",
    "https://www.xtrawine.com/en-nl/products/ca-dei-frati-cuvee-dei-frati-dosaggio-zero",
    "https://www.xtrawine.com/en-nl/products/cesarini-sforza-aquila-reale-brut-riserva-2013",
    "https://www.xtrawine.com/en-nl/products/david-leclapart-champagne-1er-cru-laphrodisiaque-pas-dose",
    "https://www.xtrawine.com/en-nl/products/domaine-de-villaine-rully-blanc-1er-cru-2021",
    "https://www.xtrawine.com/en-nl/products/ca-dei-frati-lugana-privilegio-di-famiglia-brolettino-2017",
    "https://www.xtrawine.com/en-nl/products/ca-dei-frati-amarone-della-valpolicella-pietro-dal-cero-2018",
    "https://www.xtrawine.com/en-nl/products/weingut-steinhaus-hirsch-pinot-nero-2021",
    "https://www.xtrawine.com/en-nl/products/pojer-e-sandri-bianco-faye-2020",
    "https://www.xtrawine.com/en-nl/products/ca-dei-frati-rosa-dei-frati-rosato-magnum-2023",
    "https://www.xtrawine.com/en-nl/products/henriet-bazin-champagne-hypolite-fut-de-chene-1er-cru-blanc-de-blancs-extra-brut",
    "https://www.xtrawine.com/en-nl/products/legrand-latour-champagne-turbidite-brut-nature",
    "https://www.xtrawine.com/en-nl/products/domaine-bouchie-chatellier-pouilly-fuma-argile-a-silex-2023",
    "https://www.xtrawine.com/en-nl/products/ca-dei-frati-cuvee-dei-frati-extra-brut-rose",
    "https://www.xtrawine.com/en-nl/products/cantina-valle-isarco-aristos-gewurztraminer-2023",
    "https://www.xtrawine.com/en-nl/products/ferrari-trento-perle-brut-riserva-magnum-2018",
    "https://www.xtrawine.com/en-nl/products/de-loach-winery-chardonnay-california-heritage-reserve-2022",
    "https://www.xtrawine.com/en-nl/products/nicolas-feuillatte-champagne-grand-cru-blanc-de-blancs-millesime-brut-2015",
    "https://www.xtrawine.com/en-nl/products/robinot-lange-vin-nocturne-pineau-daunis",
]

# To filter out non-wines (if you get stuck with vermouth / spirits, etc.)
NON_WINE_KEYWORDS = {
    "gin", "whisky", "whiskey", "rum", "vodka", "tequila", "mezcal",
    "cognac", "armagnac", "brandy", "liqueur", "liqueurs", "spirit",
    "spirits", "amaro", "vermouth", "grappa", "bourbon"
}

GUIDE_MAP = {
    "LM": "Luca Maroni",
    "JS": "James Suckling",
    "RP": "Robert Parker",
    "WS": "Wine Spectator",
    "VO": "Vinous",
    "GR": "Gambero Rosso",
    "BB": "Bibenda",
    "VT": "Vitae AIS",
}

# Typical labels that appear in the text of XtraWine to “capture” key/value even if it's not a table
COMMON_LABELS = [
    "Name", "Type", "Denomination", "Vintage", "Year", "Size", "Alcohol content",
    "Area", "Region", "Country", "Vendor", "Origin", "Grape varieties", "Biologic",
    "Climate", "Soil composition", "Cultivation system", "Harvest", "Wine making",
    "Fermentation temperature", "Aging", "Allergens",
    "Color", "Perfume", "Taste",
    "Serve at", "Longevity", "Decanting time",
    "Producer", "Start up year", "Oenologist", "Bottles produced", "Hectares"
]


# ---------------------------
# Helpers
# ---------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def canonicalize_url(url: str) -> str:
    """
    Remove tracking/query params and normalize.
    """
    try:
        p = urlparse(url)
        # drop query + fragment
        cleaned = ParseResult(
            scheme=p.scheme or "https",
            netloc=p.netloc,
            path=p.path,
            params="",
            query="",
            fragment="",
        )
        return urlunparse(cleaned)
    except Exception:
        return url

def key_to_snake(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[%()\/:.,'\"’`]+", " ", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")

def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def parse_price(text: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Parse prices like "€14,50" / "€17,00" etc.
    """
    if not text:
        return None, None
    t = normalize_ws(text)
    currency = None
    if "€" in t:
        currency = "EUR"
    elif "$" in t:
        currency = "USD"
    # find number
    m = re.search(r"([0-9]{1,3}(?:[.\s][0-9]{3})*|[0-9]+)([.,][0-9]{1,2})?", t)
    if not m:
        return None, currency
    num = m.group(0)
    num = num.replace(" ", "")
    # thousands: 1.234,56 or 1,234.56 (best-effort)
    # If comma is decimal (common in EU): "14,50"
    if num.count(",") == 1 and (num.count(".") == 0):
        num = num.replace(",", ".")
    # If "1.234,56": remove dots then comma->dot
    if num.count(".") >= 1 and num.count(",") == 1:
        num = num.replace(".", "").replace(",", ".")
    try:
        return float(num), currency
    except Exception:
        return None, currency

def parse_abv(text: str) -> Optional[float]:
    """
    "15.0% by volume" -> 15.0
    """
    if not text:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    return float(m.group(1)) if m else None

def parse_size_liters(text: str) -> Optional[float]:
    """
    "0,75 l" -> 0.75 ; "1,50 l" -> 1.5
    """
    if not text:
        return None
    t = normalize_ws(text).lower()
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*l", t)
    if not m:
        return None
    val = m.group(1).replace(",", ".")
    try:
        return float(val)
    except Exception:
        return None

def parse_year_from_name(name: str) -> Optional[int]:
    if not name:
        return None
    m = re.search(r"(19\d{2}|20\d{2})\b", name)
    return int(m.group(1)) if m else None

def parse_range_c(text: str) -> Tuple[Optional[int], Optional[int]]:
    """
    "06 - 08 °C." -> (6, 8)
    """
    if not text:
        return None, None
    m = re.search(r"(\d{1,2})\s*-\s*(\d{1,2})\s*°?c", text.lower())
    if m:
        return int(m.group(1)), int(m.group(2))
    m2 = re.search(r"(\d{1,2})\s*°?c", text.lower())
    if m2:
        v = int(m2.group(1))
        return v, v
    return None, None

def parse_longevity_years(text: str) -> Tuple[Optional[int], Optional[int]]:
    """
    "05 - 10 years" -> (5, 10)
    """
    if not text:
        return None, None
    t = text.lower()
    m = re.search(r"(\d{1,2})\s*-\s*(\d{1,2})\s*years", t)
    if m:
        return int(m.group(1)), int(m.group(2))
    m2 = re.search(r"(\d{1,2})\s*years", t)
    if m2:
        v = int(m2.group(1))
        return v, v
    return None, None

def parse_grapes(text: str) -> List[Dict[str, Any]]:
    """
    "90% Nerello Mascalese, 10% Carricante" -> [{"name":"Nerello Mascalese","percentage":90}, ...]
    "Pinot Nero" -> [{"name":"Pinot Nero","percentage":None}]
    """
    if not text:
        return []
    t = normalize_ws(text)
    parts = [p.strip() for p in re.split(r"[;,]", t) if p.strip()]
    out: List[Dict[str, Any]] = []
    for p in parts:
        m = re.match(r"(?:(\d+(?:\.\d+)?)\s*%\s*)?(.*)$", p)
        if not m:
            continue
        perc = m.group(1)
        name = m.group(2).strip()
        out.append({
            "name": name,
            "percentage": float(perc) if perc is not None else None
        })
    return out

def looks_like_product_url(url: str) -> bool:
    u = url.lower()
    if "/en-nl/products/" not in u:
        return False
    # quick block for obvious spirits
    if any(k in u for k in NON_WINE_KEYWORDS):
        return False
    return True


# ---------------------------
# Extraction (HTML -> dict)
# ---------------------------

def extract_json_ld_product(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    scripts = soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)})
    for s in scripts:
        txt = (s.string or "").strip()
        if not txt:
            continue
        try:
            data = json.loads(txt)
        except Exception:
            continue

        candidates = []
        if isinstance(data, dict):
            candidates = [data]
        elif isinstance(data, list):
            candidates = [d for d in data if isinstance(d, dict)]

        for obj in candidates:
            if obj.get("@type") == "Product":
                return obj
            # sometimes in @graph
            if "@graph" in obj and isinstance(obj["@graph"], list):
                for g in obj["@graph"]:
                    if isinstance(g, dict) and g.get("@type") == "Product":
                        return g
    return None

def extract_meta(soup: BeautifulSoup) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    for tag in soup.find_all("meta"):
        prop = tag.get("property") or tag.get("name")
        content = tag.get("content")
        if prop and content:
            meta[prop.strip()] = content.strip()
    return meta

def extract_pairs_from_tables(soup: BeautifulSoup) -> Dict[str, str]:
    kv: Dict[str, str] = {}
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = [normalize_ws(td.get_text(" ", strip=True)) for td in tr.find_all(["th", "td"])]
            if len(cells) >= 2:
                k, v = cells[0], cells[1]
                if k and v and len(k) <= 80:
                    kv[k] = v
    return kv

def extract_pairs_from_dl(soup: BeautifulSoup) -> Dict[str, str]:
    kv: Dict[str, str] = {}
    for dl in soup.find_all("dl"):
        dts = dl.find_all("dt")
        dds = dl.find_all("dd")
        if len(dts) == len(dds) and len(dts) > 0:
            for dt, dd in zip(dts, dds):
                k = normalize_ws(dt.get_text(" ", strip=True))
                v = normalize_ws(dd.get_text(" ", strip=True))
                if k and v:
                    kv[k] = v
    return kv

def extract_pairs_from_text(soup: BeautifulSoup, labels: List[str]) -> Dict[str, str]:
    """
    Fallback: find common labels in the flattened page text and capture the substring until the next label.
    Works well with XtraWine because a lot of “Technical Sheet” content appears as plain text.
    """
    text = " ".join(soup.stripped_strings)
    text = normalize_ws(text)

    # find occurrences of labels (case-insensitive)
    hits: List[Tuple[int, int, str]] = []
    for lab in labels:
        for m in re.finditer(rf"\b{re.escape(lab)}\b", text, flags=re.IGNORECASE):
            hits.append((m.start(), m.end(), lab))

    if not hits:
        return {}

    hits.sort(key=lambda x: x[0])

    kv: Dict[str, str] = {}
    for i, (start, end, lab) in enumerate(hits):
        nxt_start = hits[i + 1][0] if i + 1 < len(hits) else len(text)
        raw_val = text[end:nxt_start]
        val = normalize_ws(raw_val)
        # remove trailing ":" if present at beginning
        val = re.sub(r"^\s*:\s*", "", val)
        # avoid garbage super-long captures
        if val and len(val) <= 500:
            kv[lab] = val
    return kv

def extract_description(soup: BeautifulSoup, ld_product: Optional[Dict[str, Any]]) -> Optional[str]:
    if ld_product and isinstance(ld_product.get("description"), str):
        return normalize_ws(ld_product["description"])
    # try common heading "Description"
    h = soup.find(lambda t: t.name in ("h1", "h2", "h3", "h4") and "description" in t.get_text(strip=True).lower())
    if h:
        # get next meaningful block
        nxt = h.find_next()
        if nxt:
            txt = normalize_ws(nxt.get_text(" ", strip=True))
            if txt and len(txt) > 30:
                return txt
    return None

def extract_awards(soup: BeautifulSoup, vintage_year: Optional[int]) -> List[Dict[str, Any]]:
    """
    Best-effort: find patterns like "99 LM" or "92 JS" and map to guides.
    """
    text = " ".join(soup.stripped_strings)
    text = normalize_ws(text)

    awards: List[Dict[str, Any]] = []
    seen: Set[Tuple[int, str]] = set()

    for m in re.finditer(r"\b(\d{2,3})\s+(LM|JS|RP|WS|VO|GR|BB|VT)\b", text):
        score = int(m.group(1))
        code = m.group(2)
        key = (score, code)
        if key in seen:
            continue
        seen.add(key)
        awards.append({
            "year": vintage_year,
            "guide_code": code,
            "guide": GUIDE_MAP.get(code, code),
            "score": score,
            "scale": 100 if score > 10 else None  # GR/BB/VT sometimes are “3/4/5” style; keep best-effort
        })

    return awards

def extract_pairings(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Try to capture pairings categories and a short description.
    """
    result = {"categories": [], "description": None}
    # Find heading containing "Pairings"
    h = soup.find(lambda t: t.name in ("h2", "h3", "h4") and "pairings" in t.get_text(strip=True).lower())
    if not h:
        return result

    # Collect nearby list items / text until next heading
    categories: List[str] = []
    desc: Optional[str] = None

    cursor = h
    for _ in range(10):
        cursor = cursor.find_next()
        if not cursor:
            break
        if cursor.name in ("h2", "h3", "h4") and cursor is not h:
            break
        if cursor.name in ("ul", "ol"):
            for li in cursor.find_all("li"):
                t = normalize_ws(li.get_text(" ", strip=True))
                if t and len(t) <= 40:
                    categories.append(t)
        else:
            t = normalize_ws(cursor.get_text(" ", strip=True))
            # ignore empty / too short
            if t and len(t) > 40 and desc is None:
                desc = t

    # de-dup
    dedup = []
    seen = set()
    for c in categories:
        if c.lower() in seen:
            continue
        seen.add(c.lower())
        dedup.append(c)

    result["categories"] = dedup
    result["description"] = desc
    return result

def extract_serving_info(soup: BeautifulSoup) -> Dict[str, Any]:
    text = " ".join(soup.stripped_strings)
    text = normalize_ws(text)

    # Serve at
    serve_match = re.search(r"Serve at\s*:?\s*([0-9]{1,2}\s*-\s*[0-9]{1,2}\s*°?C\.?|[0-9]{1,2}\s*°?C\.?)", text, flags=re.I)
    serve_min, serve_max = (None, None)
    if serve_match:
        serve_min, serve_max = parse_range_c(serve_match.group(1))

    # Longevity
    long_match = re.search(r"Longevity\s*:?\s*([0-9]{1,2}\s*-\s*[0-9]{1,2}\s*years|[0-9]{1,2}\s*years)", text, flags=re.I)
    lon_min, lon_max = (None, None)
    if long_match:
        lon_min, lon_max = parse_longevity_years(long_match.group(1))

    # Decanting time
    dec_match = re.search(r"Decanting time\s*:?\s*([A-Za-z0-9\s]+?)(?:\bServe at\b|\bLongevity\b|$)", text, flags=re.I)
    dec = normalize_ws(dec_match.group(1)) if dec_match else None
    if dec and len(dec) > 40:
        dec = None

    return {
        "temperature_c_min": serve_min,
        "temperature_c_max": serve_max,
        "longevity_years_min": lon_min,
        "longevity_years_max": lon_max,
        "decanting_time": dec
    }

def is_wine_by_type(type_text: Optional[str]) -> bool:
    if not type_text:
        return True  # allow unknown
    t = type_text.lower()
    if any(k in t for k in NON_WINE_KEYWORDS):
        return False
    # Typical wine markers on XtraWine: "Red still", "White still", "sparkling wine", "champagne"
    if any(k in t for k in ["still", "sparkling", "champagne", "rosé", "rose", "wine", "prosecco", "franciacorta", "spumante", "metodo classico"]):
        return True
    return True  # keep permissive; final filter can be stricter if you want

def parse_wine_page(url: str, html: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    soup = BeautifulSoup(html, "lxml")

    # Canonical URL
    canonical = None
    link_can = soup.find("link", rel=re.compile("canonical", re.I))
    if link_can and link_can.get("href"):
        canonical = canonicalize_url(link_can["href"])
    canonical = canonical or canonicalize_url(url)

    # Discover more product links in-page
    discovered = []
    for a in soup.select('a[href*="/en-nl/products/"]'):
        href = a.get("href")
        if not href:
            continue
        full = canonicalize_url(urljoin(canonical, href))
        if looks_like_product_url(full):
            discovered.append(full)
    discovered = sorted(set(discovered))

    # JSON-LD + meta
    ld_product = extract_json_ld_product(soup)
    meta = extract_meta(soup)

    # Title/name
    name = None
    if ld_product and isinstance(ld_product.get("name"), str):
        name = normalize_ws(ld_product["name"])
    if not name:
        h1 = soup.find("h1")
        if h1:
            name = normalize_ws(h1.get_text(" ", strip=True))
    if not name:
        og = meta.get("og:title")
        name = normalize_ws(og) if og else None

    # Technical sheet / KV
    kv = {}
    kv.update(extract_pairs_from_tables(soup))
    kv.update({k: v for k, v in extract_pairs_from_dl(soup).items() if k not in kv})
    # Fallback: text capture by common labels
    fallback_kv = extract_pairs_from_text(soup, COMMON_LABELS)
    for k, v in fallback_kv.items():
        if k not in kv:
            kv[k] = v

    # Normalize kv into snake_case dict (keep raw too)
    technical_sheet = {key_to_snake(k): v for k, v in kv.items()}

    # Core fields best-effort from technical sheet
    type_text = technical_sheet.get("type") or technical_sheet.get("product_type")
    vendor = technical_sheet.get("vendor")
    denomination = technical_sheet.get("denomination")
    region = technical_sheet.get("region")
    country = technical_sheet.get("country")
    area = technical_sheet.get("area")
    grape_text = technical_sheet.get("grape_varieties") or technical_sheet.get("grape_variety")
    abv_text = technical_sheet.get("alcohol_content")
    size_text = technical_sheet.get("size")

    # vintage/year
    vintage = technical_sheet.get("vintage") or technical_sheet.get("year")
    vintage_year = None
    if vintage:
        ym = re.search(r"(19\d{2}|20\d{2})", vintage)
        if ym:
            vintage_year = int(ym.group(1))
    if vintage_year is None and name:
        vintage_year = parse_year_from_name(name)

    # Pricing from JSON-LD offers (best-effort)
    price = None
    currency = None
    availability = None
    if ld_product:
        offers = ld_product.get("offers")
        if isinstance(offers, dict):
            price = offers.get("price")
            currency = offers.get("priceCurrency")
            availability = offers.get("availability")
        elif isinstance(offers, list) and offers:
            o0 = offers[0]
            if isinstance(o0, dict):
                price = o0.get("price")
                currency = o0.get("priceCurrency")
                availability = o0.get("availability")

    # Fallback price from meta
    if price is None:
        for k in ("product:price:amount", "og:price:amount"):
            if k in meta:
                p, cur = parse_price(meta[k])
                price = p
                currency = currency or cur

    # Coerce price if string numeric
    if isinstance(price, str):
        p, cur = parse_price(price)
        price = p
        currency = currency or cur
    if isinstance(price, (int, float)):
        price = float(price)

    # Images
    images: List[str] = []
    if ld_product:
        img = ld_product.get("image")
        if isinstance(img, str):
            images.append(img)
        elif isinstance(img, list):
            images.extend([x for x in img if isinstance(x, str)])
    og_img = meta.get("og:image")
    if og_img:
        images.append(og_img)
    images = [canonicalize_url(i) for i in images if i]
    images = list(dict.fromkeys(images))  # de-dup keep order
    main_image = images[0] if images else None

    # Description
    description = extract_description(soup, ld_product)

    # Tasting notes
    tasting = {
        "color": technical_sheet.get("color"),
        "perfume": technical_sheet.get("perfume"),
        "taste": technical_sheet.get("taste"),
    }

    # Serving
    serving = extract_serving_info(soup)

    # Pairings
    pairings = extract_pairings(soup)
    # also try from technical sheet field if exists
    if not pairings.get("description") and technical_sheet.get("pairings"):
        pairings["description"] = technical_sheet.get("pairings")

    # Grapes structured
    grapes = parse_grapes(grape_text) if grape_text else []

    # ABV + size
    abv = parse_abv(abv_text) if abv_text else None
    size_l = parse_size_liters(size_text) if size_text else None

    # Awards
    awards = extract_awards(soup, vintage_year)

    # Basic producer info (best-effort from technical sheet)
    producer_info = {
        "name": vendor,
        "start_up_year": None,
        "oenologist": None,
        "bottles_produced": None,
        "hectares": None,
        "description": None
    }
    # if fallback_kv captured these labels, map them
    sy = technical_sheet.get("start_up_year")
    if sy:
        m = re.search(r"(19\d{2}|20\d{2})", sy)
        producer_info["start_up_year"] = int(m.group(1)) if m else None
    producer_info["oenologist"] = technical_sheet.get("oenologist")
    producer_info["bottles_produced"] = technical_sheet.get("bottles_produced")
    producer_info["hectares"] = technical_sheet.get("hectares")

    # Decide if this is wine enough
    if not is_wine_by_type(type_text):
        return None, discovered

    data: Dict[str, Any] = {
        "schema_version": "1.0",
        "source": {
            "site": "xtrawine",
            "url": canonical,
            "locale": "en-nl",
            "scraped_at": now_iso(),
        },
        "product": {
            "name": name,
            "vendor": vendor,
            "producer": vendor,  # same in XtraWine (Vendor) normalmente
            "type": type_text,
            "vintage_year": vintage_year,
            "denomination": denomination,
            "country": country,
            "region": region,
            "area": area,
            "size_liters": size_l,
            "alcohol_by_volume": abv,
            "grape_varieties": grapes,
        },
        "pricing": {
            "currency": currency,
            "price": price,
            "availability": availability,
        },
        "tasting_notes": tasting,
        "serving": serving,
        "pairings": pairings,
        "awards": awards,
        "producer_info": producer_info,
        "media": {
            "main_image": main_image,
            "images": images,
        },
        # Esto es lo más importante para no perder info (toda la ficha técnica tal cual)
        "technical_sheet": technical_sheet,
        "raw": {
            "technical_sheet_raw": kv,
        },
    }

    return data, discovered


# ---------------------------
# HTTP / crawl
# ---------------------------

def build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; WineCrawler/1.0; +https://example.com/bot)",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
    })
    return s

def fetch_html(session: requests.Session, url: str, max_retries: int = 4, timeout: int = 25) -> str:
    last_err = None
    for attempt in range(max_retries):
        try:
            r = session.get(url, timeout=timeout, allow_redirects=True)
            if r.status_code in (429, 500, 502, 503, 504):
                # backoff
                sleep_s = (2 ** attempt) + random.random()
                time.sleep(sleep_s)
                continue
            r.raise_for_status()
            return r.text
        except Exception as e:
            last_err = e
            time.sleep((2 ** attempt) + random.random())
    raise RuntimeError(f"Failed to fetch {url}. Last error: {last_err}")

def polite_sleep(delay: float, jitter: float) -> None:
    time.sleep(max(0.0, delay + random.uniform(-jitter, jitter)))


# ---------------------------
# Main
# ---------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=100, help="Max wines to collect (default 100).")
    ap.add_argument("--out", type=str, default="xtrawine_wines.json", help="Output JSON array filename.")
    ap.add_argument("--ndjson", type=str, default="xtrawine_wines.ndjson", help="Output NDJSON streaming filename.")
    ap.add_argument("--delay", type=float, default=1.2, help="Delay between requests (seconds).")
    ap.add_argument("--jitter", type=float, default=0.8, help="Random jitter added/subtracted to delay (seconds).")
    args = ap.parse_args()

    out_json = Path(args.out).resolve()
    out_ndjson = Path(args.ndjson).resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)

    session = build_session()

    queue: List[str] = [canonicalize_url(u) for u in SEED_WINE_URLS]
    seen: Set[str] = set(queue)
    processed: Set[str] = set()

    wines: List[Dict[str, Any]] = []

    # streaming write: append mode
    with out_ndjson.open("w", encoding="utf-8") as f_nd:
        while queue and len(wines) < args.max:
            url = queue.pop(0)
            if url in processed:
                continue
            processed.add(url)

            try:
                html = fetch_html(session, url)
                wine_data, discovered = parse_wine_page(url, html)

                # enqueue discovered
                for d in discovered:
                    d = canonicalize_url(d)
                    if d not in seen:
                        seen.add(d)
                        queue.append(d)

                if wine_data is None:
                    polite_sleep(args.delay, args.jitter)
                    continue

                wines.append(wine_data)

                # write one line immediately
                f_nd.write(json.dumps(wine_data, ensure_ascii=False) + "\n")
                f_nd.flush()

                print(f"[{len(wines)}/{args.max}] OK  {wine_data['product'].get('name') or url}")
            except Exception as e:
                print(f"[ERR] {url} -> {e}")

            polite_sleep(args.delay, args.jitter)

    # final JSON array
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(wines, f, ensure_ascii=False, indent=2)

    print(f"\nDone. NDJSON: {out_ndjson}")
    print(f"Done. JSON:   {out_json}")
    print(f"Collected: {len(wines)} wines. Seen URLs: {len(seen)}. Processed: {len(processed)}.")

if __name__ == "__main__":
    main()

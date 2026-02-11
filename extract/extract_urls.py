#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import time
import random
import requests
import xml.etree.ElementTree as ET
from typing import List, Set


NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
}

def _sleep(delay: float = 0.8, jitter: float = 0.4) -> None:
    time.sleep(max(0.0, delay + random.uniform(-jitter, jitter)))

def _get_xml(url: str, session: requests.Session, timeout: int = 30) -> str:
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text

def get_en_nl_product_urls(limit: int = 80) -> List[str]:
    """
    Descarga el sitemap index de en-nl, encuentra los sitemap_products_*.xml
    y devuelve URLs de producto que cumplan: https://www.xtrawine.com/en-nl/products/...
    """
    base = "https://www.xtrawine.com"
    sitemap_index_url = f"{base}/sitemap.xml"

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; VinumCrawler/1.0)",
        "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })

    index_xml = _get_xml(sitemap_index_url, session)
    root = ET.fromstring(index_xml)

    # Extrae sitemaps de productos
    product_sitemaps: List[str] = []
    for sm in root.findall("sm:sitemap", NS):
        loc = sm.find("sm:loc", NS)
        if loc is None or not loc.text:
            continue
        url = loc.text.strip()
        # Shopify style: /en-nl/sitemap_products_1.xml?... (queremos solo esos)
        if "/en-nl/sitemap_products_" in url:
            product_sitemaps.append(url)

    if not product_sitemaps:
        raise RuntimeError(
            "No encontré /en-nl/sitemap_products_*.xml en el sitemap index. "
            "Revisa si la URL del sitemap index cambió."
        )

    product_urls: List[str] = []
    seen: Set[str] = set()

    # Itera cada sitemap de productos hasta completar "limit"
    for sm_url in product_sitemaps:
        _sleep()
        sm_xml = _get_xml(sm_url, session)
        sm_root = ET.fromstring(sm_xml)

        for url_el in sm_root.findall("sm:url", NS):
            loc = url_el.find("sm:loc", NS)
            if loc is None or not loc.text:
                continue

            u = loc.text.strip()

            # Criterio exacto: en-nl/products
            if not u.startswith(f"{base}/en-nl/products/"):
                continue

            # Filtra cosas raras si aparecen (opcional)
            if any(k in u.lower() for k in ["gin", "whisky", "vodka", "tequila", "rum", "grappa", "vermouth"]):
                continue

            if u not in seen:
                seen.add(u)
                product_urls.append(u)

            if len(product_urls) >= limit:
                return product_urls

    return product_urls

def print_as_python_list(urls: List[str]) -> None:
    print("SEED_WINE_URLS: List[str] = [")
    for u in urls:
        print(f'    "{u}",')
    print("]")

if __name__ == "__main__":
    n = 100
    if len(sys.argv) > 1:
        n = int(sys.argv[1])

    urls = get_en_nl_product_urls(limit=n)
    print_as_python_list(urls)

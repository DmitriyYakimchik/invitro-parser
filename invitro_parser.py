import logging
import re
from typing import Dict

from bs4 import BeautifulSoup

from utils import clean_text

logger = logging.getLogger(__name__)


def parse_analysis_page(html: str, url: str) -> dict[str, str]:
    """Parse Invitro analysis page and extract structured data."""
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ")

    # Name
    name = ""
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        name = clean_text(h1.get_text())
    else:
        a_name = soup.select_one(".analyzes-item__title a")
        if a_name:
            name = clean_text(a_name.get_text())

    # Category and subcategory (from breadcrumbs)
    category, subcategory = "", ""
    breadcrumbs = soup.select(".bread-crumbs__list li")
    if breadcrumbs:
        relevant_crumbs = []
        for crumb in breadcrumbs[2:]:
            origin_text = crumb.get("origin_text", "")
            if origin_text:
                relevant_crumbs.append(origin_text)
            else:
                link = crumb.find("a")
                if link:
                    relevant_crumbs.append(link.get_text(strip=True))
                else:
                    current = crumb.find("span", class_="bread-crumbs__current")
                    if current:
                        relevant_crumbs.append(current.get_text(strip=True))

        if len(relevant_crumbs) >= 1:
            category = relevant_crumbs[0]
        if len(relevant_crumbs) >= 2:
            subcategory = relevant_crumbs[1]

    # INVITRO internal code
    inv_code = ""
    article_section = soup.find("div", class_="info-block__section info-block__section--article")
    if article_section:
        title_span = article_section.find("span", class_="info-block__title")
        if title_span and "Артикул:" in title_span.get_text():
            price_span = article_section.find("span", class_="info-block__price")
            if price_span:
                inv_code = clean_text(price_span.get_text(strip=True))
                logger.debug(f"Found Invitro code in article section: {inv_code}")

    if not inv_code:
        inv_node = soup.select_one(".analyzes-item__head--number span")
        if inv_node:
            inv_text = inv_node.get_text(strip=True)
            inv_match = re.search(r"№\s*(\d+)", inv_text)
            if inv_match:
                inv_code = inv_match.group(1)
            else:
                inv_code = clean_text(inv_text.replace("№", ""))
            logger.debug(f"Found Invitro code in head number: {inv_code}")

    if not inv_code:
        inv_match = re.search(r"Артикул:\s*(\S+)", text)
        if inv_match:
            inv_code = clean_text(inv_match.group(1))
            logger.debug(f"Found Invitro code in text: {inv_code}")

    # Ministry of Health code
    mz_code = ""
    desc_node = soup.select_one(".analyzes-item__description")
    if desc_node:
        desc_txt = desc_node.get_text(" ", strip=True)
        m = re.search(r"[A-ZА-Я]\d{2}\.\d{2}\.\d{3}", desc_txt)
        if m:
            mz_code = m.group(0)
    if not mz_code:
        m = re.search(r"[A-ZА-Я]\d{2}\.\d{2}\.\d{3}", text)
        if m:
            mz_code = m.group(0)

    # Turnaround time
    tat = ""
    tat_node = soup.select_one(".analyzes-item__add--list-item span")
    if tat_node and tat_node.get_text(strip=True):
        tat = clean_text(tat_node.get_text())
    else:
        m = re.search(r"\d+\s*(?:рабоч|календарн)[а-я]*\s*д(?:ень|ня|ней)", text, re.IGNORECASE)
        if m:
            tat = clean_text(m.group(0))

    # Price
    price = ""
    p_node = soup.select_one(".info-block__price--total")
    if p_node:
        price = clean_text(p_node.get_text())
    else:
        p_node2 = soup.select_one(".analyzes-item__total--sum")
        if p_node2:
            price = clean_text(p_node2.get_text())
        else:
            m = re.search(r"\b\d[\d\s]*(?:[.,]\d{2})?\s*(?:₽|руб|руб\.)", text)
            if m:
                price = clean_text(m.group(0))

    return {
        "Категория": category,
        "Подкатегория": subcategory,
        "Название анализа": name,
        "Код анализа во внутренней системе Invitro": inv_code,
        "Код анализа по номенклатуре МЗ РФ (если есть)": mz_code,
        "Срок выполнения анализа": tat,
        "Стоимость анализа": price,
    }

import re
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag
import time
import sys

import pandas as pd

from .config import BASE_URL, BRAND_PATHS, EXPECTED_SPEC_KEYS, SESSION


def scrape_tw_racquets(
    save_file: bool = False, save_path: str | None = None, 
    save_html: bool = False, save_html_path: str | None = None,
    verbose: bool = False
) -> pd.DataFrame:
    """Orchestration function that uses below functions to
    iteratively scrape each racquet's page on each brand page.

    Args:
        save_file (bool): Whether or not to save the df as a CSV. Defaults to False.
        save_path (str): Path for saved CSV file. Required if save_file = True. Defaults to None.

    Returns:
        pd.DataFrame: Dataframe containing features for each scraped racquet
    """
    # Early arg checks
    if save_file and save_path is None:
        raise ValueError(f"Incompatible args: save_file is set to True but save_path is None. Please set a save path.")
    
    if save_html and save_html_path is None:
        raise ValueError(f"Incompatible args: save_html is set to True but save_html_path is None. Please set a save path for the HTML files.")

    rows: list[dict[str, object]] = []

    brand_urls = get_brand_urls()
    brand_counter = 0
    for brand_url in brand_urls:
        (
            print(f"Scraping brand {brand_counter + 1} of {len(brand_urls)}")
            if verbose
            else None
        )

        racquet_urls = get_racquet_urls(brand_url=brand_url)
        racquet_counter = 0

        for racquet_url in get_racquet_urls(brand_url=brand_url):
            (
                print(f"Scraping racquet {racquet_counter + 1} of {len(racquet_urls)}")
                if verbose
                else None
            )

            try:
                soup = _get_soup(racquet_url)

            except requests.RequestException as e:
                print(
                    f"Request Exception: {e}\nContinuing to next racquet...",
                    file=sys.stderr,
                )
                continue

            info = get_racquet_info(racquet_soup=soup, racquet_url=racquet_url)
            specs = get_racquet_specs(racquet_soup=soup)

            rows.append({**info, **specs})  # Unpack info and specs then append

            racquet_counter += 1
            
            time.sleep(1.0) # wait 1 sec between fetching every racquet for politeness

        brand_counter += 1

    df = pd.DataFrame(rows)

    for k in EXPECTED_SPEC_KEYS:
        if k not in df.columns:
            df[k] = None

    if save_file:
        if save_path is None:
            raise ValueError("save_path must be provided when save_file=True")
        df.to_csv(save_path, index=False)

    return df


def get_brand_urls() -> list[str]:
    """Concat BASE_URL with each suffix in
    BRAND_PATHs.

    Returns:
        list[str]: List of brand page URLs
    """
    return [urljoin(BASE_URL, path) for path in BRAND_PATHS]


def get_racquet_urls(brand_url: str) -> list[str]:
    """Find all a tags in a brand's racquet table
    and extract the racquet URLs into a list.

    Args:
        brand_url (str): URL of racquet brand's page

    Returns:
        list[str]: List of product URLs for the inputted brand page
    """
    soup = _get_soup(url=brand_url)

    racquet_urls: list[str] = []

    racquet_tags = soup.find_all("a", class_="cattable-wrap-cell-info")

    # Get hrefs in a tags
    for tag in racquet_tags:
        if not isinstance(tag, Tag):  # Skips None
            continue

        href = tag.get("href")

        if not isinstance(href, str):  # Skips None
            continue

        href = href.strip()

        full_href = urljoin(BASE_URL, href)
        racquet_urls.append(full_href)

    seen: set[str] = set()
    deduped_urls: list[str] = []

    for url in racquet_urls:
        if url not in seen:
            deduped_urls.append(url)
            seen.add(url)

    return deduped_urls


def get_racquet_info(
    racquet_soup: BeautifulSoup, racquet_url: str
) -> dict[str, str | None]:
    """Extract racquet metadata from a given racquet URL

    Args:
        racquet_soup (BeautifulSoup): Beautiful soup content from a racquet's product page
        racquet_url (str): URL to racquet's product page

    Returns:
        dict[str, str | None]: Dictionary of feature:value pairs to feed into a DataFrame
    """
    # IMAGE
    image_tag = racquet_soup.select_one("img.main_image.is-zoomable")
    image_src = image_tag.get("src") if isinstance(image_tag, Tag) else None
    image_url = (
        urljoin(BASE_URL, image_src.strip()) if isinstance(image_src, str) else None
    )

    # NAME
    name_tag = racquet_soup.find("h1", class_="desc_top-head-title")
    name = name_tag.get_text(strip=True) if isinstance(name_tag, Tag) else None

    # RATING
    rating_tag = racquet_soup.find("div", class_="review_agg")
    rating = rating_tag.get_text(strip=True) if isinstance(rating_tag, Tag) else None
    
    # RATING COUNT
    rating_ct_tag = racquet_soup.find("a", id = "no-select")
    rating_ct_tag_text = rating_ct_tag.get_text(strip = True) if isinstance (rating_ct_tag, Tag) else None
    
    if rating_ct_tag_text:
        rating_ct = re.findall(r"\d+", rating_ct_tag_text)
        
        if len(rating_ct) == 0: # If racquet has no reviews -> text will be "Submit a Review" and re will return [] -> set those to None
            rating_ct = None
        else:
            rating_ct = rating_ct[0]
    else:
        rating_ct = None
    
    # PRICE
    price_tag = racquet_soup.find("span", class_="afterpay-full_price")
    price = price_tag.get_text(strip=True) if isinstance(price_tag, Tag) else None
    
    # DESCRIPTION - TRY PRODUCT_CHARS FIRST THEN FALLBACK TO PRODUCT_OVERVIEW
    description = None
    
    span = racquet_soup.find("span", attrs = {"id": "product_chars"})
    if isinstance(span, Tag):
        text = span.get_text(" ", strip = True)
        description = text if text else None
        
    if description is None:
        container = racquet_soup.find("div", attrs = {"id": "product_overview"})
        
        if isinstance(container, Tag):
            paragraphs = container.find_all("p")
            text = (" ".join([p.get_text(" ", strip = True) for p in paragraphs]))
            description = text if text else None
        
    return {
        "racquet_url": racquet_url,
        "racquet_img": image_url,
        "racquet_name": name,
        "racquet_rating": rating,
        "racquet_rating_count": rating_ct,
        "racquet_price": price,
        "racquet_description": description,
    }


def get_racquet_specs(racquet_soup: BeautifulSoup) -> dict[str, str | None]:
    """Read Spec Table and collect specs into a dictionary
    for a given racquet page.

    Args:
        racquet_soup (BeautifulSoup): Beautiful Soup content from parsed racquet page

    Returns:
        dict[str,str | None]: Dictionary of spec:value pairs to feed into a DataFrame
    """

    # Get div for Spec Table
    specs_div_tag = racquet_soup.find("div", class_="check_read-inner")

    if not isinstance(specs_div_tag, Tag):  # If Spec Table DNE
        return {
            "head_size": None,
            "length": None,
            "strung_weight": None,
            "balance": None,
            "swingweight": None,
            "stiffness": None,
            "beam_width": None,
            "composition": None,
            "power_level": None,
            "stroke_style": None,
            "swing_speed": None,
            "racquet_colors": None,
            "grip_type": None,
            "string_pattern": None,
            "string_tension": None,
        }

    else:
        tbody_tag = specs_div_tag.find("tbody")

    if not isinstance(tbody_tag, Tag):  # If Spec Table DNE/isn't usable
        return {
            "head_size": None,
            "length": None,
            "strung_weight": None,
            "balance": None,
            "swingweight": None,
            "stiffness": None,
            "beam_width": None,
            "composition": None,
            "power_level": None,
            "stroke_style": None,
            "swing_speed": None,
            "racquet_colors": None,
            "grip_type": None,
            "string_pattern": None,
            "string_tension": None,
        }

    else:
        td_tags = tbody_tag.find_all("td", class_=re.compile("Specs"))

    key_mapping: dict[str, str] = {":": "", " ": "_"}
    keys_translation = str.maketrans(key_mapping)

    racquet_specs_payload: dict[str, str | None] = {}

    if td_tags:
        for tag in td_tags:
            if not isinstance(tag, Tag):
                continue

            label_tag = tag.find("strong")
            if label_tag:
                if not isinstance(label_tag, Tag):
                    continue

                label = (
                    label_tag.get_text(strip=True).lower().translate(keys_translation)
                )
                value = tag.get_text(" ", strip=True)
                _, sep, rest = value.partition(":")
                value = rest.strip() if sep else value
                value = value or None

            else:
                label = "other"
                value = tag.get_text(strip=True)

            racquet_specs_payload[label] = value

        return racquet_specs_payload

    else:
        return {
            "head_size": None,
            "length": None,
            "strung_weight": None,
            "balance": None,
            "swingweight": None,
            "stiffness": None,
            "beam_width": None,
            "composition": None,
            "power_level": None,
            "stroke_style": None,
            "swing_speed": None,
            "racquet_colors": None,
            "grip_type": None,
            "string_pattern": None,
            "string_tension": None,
        }


def _get_soup(url: str) -> BeautifulSoup:
    """Tries to fetch html content of a URL.
    Tries 3 times (with pause in between) and raises
    if unsuccessful.
    """
    for attempt in range(3):
        try:
            response = SESSION.get(url, timeout=30)
            response.raise_for_status()

            return BeautifulSoup(response.content, "html.parser")

        except requests.RequestException:
            if attempt == 2:
                raise

            time.sleep(1.5 * (attempt + 1))

    raise RuntimeError(f"Failed to fetch {url} contents")

import json
import re
from typing import Dict, Optional

from bs4 import BeautifulSoup

from src.loggers import logger


class ListingParser:
    """
    Parses listing pages to to extract apartment links.
    """

    def __init__(self, html: str):
        """
        Initializes the parser with the provided HTML content.

        :param html: HTML content of the listing page
        """
        self.soup = BeautifulSoup(html, "lxml")

    def parse_apartment_links(self) -> list:
        """
        Extracts apartment links from the listing page.

        :return: List of apartment URLs
        """
        links = []
        cards = self.soup.find_all("article", {"data-name": "CardComponent"})
        for card in cards:
            try:
                link_tag = card.find("a", class_="_93444fe79c--link--eoxce")
                if link_tag and "href" in link_tag.attrs:
                    links.append(link_tag["href"])
            except Exception as e:
                logger.warning(f"Error parsing link: {e}")

        logger.info(f"Found {len(links)} listings")
        return links


class DetailParser:
    def __init__(self, html: str):
        """
        Initializes the parser with raw HTML content.

        :param html: HTML content of the detail page.
        """
        self.soup = BeautifulSoup(html, "lxml")
        self.details = {
            "title": None,
            "price": None,
            "price_currency": None,
            "description": None,
            "address": None,
            "images": [],
            "date_published": None,
            "rooms": None,
            "area": None,
        }

    def __parse_json_ld(self) -> None:
        """
        Extracts structured data (JSON-LD) from the page.

        Returns:
            dict: A dictionary containing structured details.
        """
        ld_json_tags = self.soup.find_all("script", type="application/ld+json")
        for tag in ld_json_tags:
            try:
                data = json.loads(tag.string or "{}")

                if isinstance(data, dict) and data.get("@type") == "Product":
                    self.details["title"] = data.get("name")
                    self.details["description"] = data.get("description")

                    if "offers" in data and isinstance(data["offers"], dict):
                        self.details["price"] = data["offers"].get("price")
                        self.details["price_currency"] = data["offers"].get("priceCurrency")

                    if isinstance(data.get("image"), list):
                        self.details["images"] = data["image"][:5]

            except json.JSONDecodeError:
                logger.warning("[JSON-Decode] Failed to parse one of the LD+JSON blocks")

    def __parse_fallback_data(self) -> None:
        """
        Extracts missing details from visible HTML elements.

        Returns:
            dict: A dictionary containing fallback extracted details.
        """
        if not self.details.get("title"):
            title_tag = self.soup.find("span", {"data-mark": "OfferTitle"})
            if title_tag:
                self.details["title"] = title_tag.get_text(strip=True)

        if not self.details.get("price"):
            price_tag = self.soup.find("span", {"data-mark": "MainPrice"})
            if price_tag:
                self.details["price"] = price_tag.get_text(strip=True)

        if not self.details.get("address"):
            address_block = self.soup.find("div", {"data-name": "AddressContainer"})
            if address_block:
                address_parts = [a.get_text(strip=True) for a in address_block.find_all("a")]
                self.details["address"] = ", ".join(address_parts) if address_parts else None

        if not self.details.get("title"):
            date_tag = self.soup.find("div", {"data-mark": "CreationDate"})
            if date_tag:
                self.details["date_published"] = date_tag.get_text(strip=True)

        if not self.details.get("rooms"):
            match = re.search(r"(\d+)\-?комн", self.details["title"].lower())
            if match:
                self.details["rooms"] = match.group(1)

        if not self.details.get("area"):
            area_block = self.soup.find("div", {"data-name": "ObjectSummaryDescription"})
            if area_block:
                self.details["area"] = area_block.get_text(strip=True)

    def __parse_offer_summary(self) -> dict:
        """
        Extracts apartment and building details from the OfferSummaryInfoItem block.

        Returns:
            dict: A dictionary containing property details.
        """

        items = self.soup.find_all("div", {"data-name": "OfferSummaryInfoItem"})
        for item in items:
            key_tag = item.find("p", class_="a10a3f92e9--color_gray60_100--r_axa")
            value_tag = item.find("p", class_="a10a3f92e9--color_text-primary-default--vSRPB")

            if key_tag and value_tag:
                key = key_tag.get_text(strip=True)
                value = value_tag.get_text(strip=True)
                self.details[key] = value

    def parse_apartment_details(self) -> Dict[str, Optional[str]]:
        """
        Extracts the main details of an apartment from the Cian detail page.

        Returns:
            dict: A dictionary containing extracted information.
        """
        try:
            self.__parse_json_ld()
            self.__parse_fallback_data()
            self.__parse_offer_summary()

        except Exception as e:
            logger.warning(f"[parse_apartment_details] An error occurred: {e}")

        return self.details

from selenium import webdriver
from bs4 import BeautifulSoup
from collections import defaultdict
import os
import json
import wget
import csv
import re

class Scraper():
    def __init__(self):
        self.product_link_list = []
        self.image_links = {}
        self.prod_details_map = {}
        self.prod_details_map_fields = ['Product Name', 'SKU', 'M.R.P.', 'Price', 'Description', 'Availability', 'Images']
        self.product_links_cache = set()

    def get_individual_product(self, url):
        print ("Getting URL: %s" % url)
        self.browser.get(url)
        soup=BeautifulSoup(self.browser.page_source)

        # get product name:
        prod_name_container = soup.find('h1', attrs={"style": 'text-align: center;'})
        prod = prod_name_container.text

        # get main image URL:
        main_img_link = soup.select_one('.thumbnail')
        self.image_links[prod] = [main_img_link['href']]

        # get additional images URL:
        image_containers = soup.select('.owl-item')
        for imgc in image_containers:
            imgls = imgc.find_all('a')
            for imgl in imgls:
                link = imgl.get('data-image')
                if link is not None:
                    self.image_links[prod].append(link)

        # get product details:
        # Keep it in HTML since Shopify supports it.
        description_container = soup.find('div', id='tab-description')
        prod_description = str(description_container)


        #get price details table
        table_container_ = soup.find("ul", class_="list-unstyled price-desc")
        table_content = str(table_container_.contents[1])
        table = BeautifulSoup(table_content)
        rows = table.find_all('tr')


        # Construct product details map
        final_list = []
        intermediate_list = []
        for tr in rows:
            for td in tr.find_all("td"):
                if td.text:
                    stemmed_text = re.sub('[:\u20b9]+', '', td.text)
                    stemmed_text = re.sub('  FREE SHIPPING', '', stemmed_text)
                    stemmed_text = re.sub('  (Free delivery)', '', stemmed_text)
                    intermediate_list.append(stemmed_text)

            if intermediate_list:
                final_list.append(intermediate_list)
            intermediate_list = []
        # 'M.R.P.', 'Price', 'SKU', 'Availability'
        data = {item[0]: item[1:][0] for item in final_list}
        for field in self.prod_details_map_fields:
            if field not in data:
                data[field] = ""
        data['Product Name'] = prod
        data['Description'] = prod_description.strip()
        data['Images'] = '\n'.join(self.image_links[prod]).strip()
        self.prod_details_map[prod] = data

    def get_products(self):
        self.browser=webdriver.Firefox()
        with open('start_url.list', 'r') as start_urls_file:
            start_urls_list = start_urls_file.readlines()
        with open('products_link.list', 'r') as prod_link_list_file:
            self.product_links_cache = set(prod_link_list_file.readlines())
        if not self.product_links_cache:
            for url in start_urls_list:
                url = url.strip()
                url = url.replace(' ', '')
                if url:
                    self.browser.get(url)
                    soup=BeautifulSoup(self.browser.page_source)
                    prods = soup.select('.caption')
                    with open('products_link.list', 'w') as prod_link_list_file:
                        for prod in prods:
                            links = prod.find_all('a')
                            for link in links:
                                self.product_link_list.append(link['href'])
                                prod_link_list_file.write(link['href'])
        else:
            self.product_link_list = self.product_links_cache

    def main(self):
        self.get_products()
        try:
            # read existing log to avoid duplicate downloads
            with open('log.txt', 'r') as log:
                log_contents = set(log.readlines())
            # Collect text data (Title, Price, Descriptions)
            with open('log.txt', 'w') as log:
                for url in self.product_link_list:
                    if url and url not in log_contents:
                        self.get_individual_product(url)
                        log_contents.add(url)
                log.writelines(log_contents)

                # Download images, write data.CSV file for each product
                
                download_dir = os.path.join(os.getcwd(), 'downloads')
                os.makedirs(download_dir, exist_ok=True)
                os.chdir(download_dir)
                with open('data.json', 'w') as jsonfile:
                    jsonfile.write(json.dumps(self.prod_details_map))
                with open('data.csv', 'w') as csvfile:
                    csvwriter = csv.DictWriter(csvfile, fieldnames=self.prod_details_map_fields)
                    csvwriter.writeheader()

                    for prod in self.prod_details_map:
                        csvwriter.writerow(self.prod_details_map[prod])
        finally:
            if self.browser:
                self.browser.close()
                self.browser.quit()

if __name__ == "__main__":
    Scraper().main()
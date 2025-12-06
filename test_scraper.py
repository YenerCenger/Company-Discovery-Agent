"""Quick test script for scrapers"""
from scrapers.company_scraper import CompanyScraper

# Test company scraper
scraper = CompanyScraper()
companies = scraper.search_companies('Miami', 'USA', limit=3)

print(f'\nFound {len(companies)} companies:')
for c in companies:
    print(f'  - {c["name"]} ({c["source"]})')

print('\nCompany scraper test passed!')

import time

from bs4 import BeautifulSoup
from dataclasses import dataclass
from selenium import webdriver

from common.engine import Engine


@dataclass
class SearchResultItem:
  title: str = ''
  link: str = ''


@dataclass
class ScrapeResult:
  items: [SearchResultItem]
  captcha: bool = False
  no_results: bool = False

  def append_scrape_result(self, other):
    if other.captcha == True:
      self.captcha = True

    elif other.no_results == True:
      self.no_results = True
    
    else:
      self.items += other.items


@dataclass
class SearchResults:
  engine: str # TODO change type to Engine everywhere
  query: str
  items: [SearchResultItem]
  captcha: bool = False
  no_results: bool = True
  internal_log: str = ''


class Scraper():
  
  search_refs = {
    Engine.GOOGLE.value: 'https://www.google.com/search?q=',
    Engine.STARTPAGE.value: 'https://www.startpage.com/do/dsearch?query=',
    Engine.BING.value: 'https://www.bing.com/search?q=',
    Engine.DUCKDUCKGO.value: 'https://duckduckgo.com/?q=',
    Engine.ASK.value: 'https://www.ask.com/web?o=0&l=dir&qo=homepageSearchBox&q=',
    Engine.MOJEEK.value: 'https://www.mojeek.com/search?q=',
    Engine.EXALEAD.value: 'http://www.exalead.com/search/web/results/?q=',
    Engine.LYCOS.value: 'https://search.lycos.com/web/?q=',
    Engine.YANDEX.value: 'https://yandex.ru/search/?text=',
    Engine.SWISSCOWS.value: 'https://swisscows.com/web?query='
  }

  secs_to_load_page = 3


  def __init__(self, user_agent: str, driver: webdriver.Firefox, query: str, engine: str, with_omitted_results: bool):
    self.user_agent = user_agent
    self.driver = driver
    self.query = query
    self.engine = engine
    self.soup = self._make_soup(with_omitted_results)


  def obtain_first_page_search_results(self) -> SearchResults:
    return self._obtain_search_results(all_pages=False)
  

  def obtain_all_pages_search_results(self) -> SearchResults:
    return self._obtain_search_results(all_pages=True)


  def _make_soup(self, with_omitted_results: bool) -> BeautifulSoup:
    url = f'{self.search_refs[self.engine]}{self.query}'
    if with_omitted_results:
      if self.engine == Engine.GOOGLE.value:
        url += '&filter=0'

    self.driver.get(url)
    time.sleep(self.secs_to_load_page)

    return BeautifulSoup(self.driver.page_source, 'lxml')


  def _obtain_all_pages_scrape_result(self) -> ScrapeResult:
    scrape_results = ScrapeResult(items=[])
    soup = self.soup

    while soup != None:
      scrape_results.append_scrape_result(self._scrape())
      soup = self._get_next_soup()

    return scrape_results


  def _obtain_search_results(self, all_pages: bool) -> SearchResults:
    scrape_result = ScrapeResult(items=[])
    internal_exception = ''

    try:
      if all_pages:
        while self.soup != None:
          scrape_result.append_scrape_result(self._scrape())
          self.soup = self._get_next_soup()
      else:
        scrape_result = self._scrape()

    except Exception as e:
      internal_exception = str(e)
    
    finally:
      internal_log = internal_exception
      if scrape_result.captcha:
        internal_log += ' | User agent: ' + self.user_agent

      search_results = SearchResults(
        engine=self.engine,
        query=self.query,
        items=scrape_result.items,
        captcha=scrape_result.captcha,
        no_results=scrape_result.no_results,
        internal_log=internal_log
      )

      return search_results


  def _get_next_soup(self) -> BeautifulSoup:
    try:
      if self.engine == Engine.GOOGLE.value:
        self.driver.find_element_by_id('pnnext').click()

      if self.engine == Engine.STARTPAGE.value:
        self.driver.find_element_by_class_name('next').click()

      if self.engine == Engine.YANDEX.value:
        self.driver.find_element_by_class_name('pager__item_kind_next').click()

    except: # no next pages
      return None

    time.sleep(self.secs_to_load_page)
    soup = BeautifulSoup(self.driver.page_source, 'lxml')

    return soup


  def _scrape(self) -> ScrapeResult:
    if self.engine == Engine.GOOGLE.value:
      return self._scrape_google()
    
    if self.engine == Engine.STARTPAGE.value:
      return self._scrape_startpage()

    if self.engine == Engine.BING.value:
      return self._scrape_bing()
    
    if self.engine == Engine.DUCKDUCKGO.value:
      return self._scrape_startpage()

    if self.engine == Engine.ASK.value:
      return self._scrape_ask()
    
    if self.engine == Engine.MOJEEK.value:
      return self._scrape_mojeek()

    if self.engine == Engine.EXALEAD.value:
      return self._scrape_exalead()
    
    if self.engine == Engine.LYCOS.value:
      return self._scrape_lycos()

    if self.engine == Engine.YANDEX.value:
      return self._scrape_yandex()

    if self.engine == Engine.SWISSCOWS.value:
      return self._scrape_swisscows()


  def _scrape_google(self) -> ScrapeResult:
    if self.soup.find(name='form', id='captcha-form') != None:
        return ScrapeResult(items=[], captcha=True)
        
    else:
      return self._common_scrape(
          title_tag_name='h3',
          title_class='DKV0Md',
          link_tag_name='div',
          link_class='NJjxre'
      )


  def _scrape_startpage(self) -> ScrapeResult:
    if self.soup.find(name='div', class_='show-results') == None:
      return ScrapeResult(items=[], captcha=True)

    else:
      return self._common_scrape(
          title_tag_name='a',
          title_class='w-gl__result-title',
          link_tag_name='a',
          link_class='w-gl__result-url',
      )


  def _scrape_bing(self) -> ScrapeResult:
    # TODO make more generic?
    titles = self.soup.find_all(name='li', class_='b_algo')
    titles = list(
      map(lambda s: s.find(name='h2').text, titles)
    )
  
    links = self.soup.find_all(name='div', class_='b_attribution')
    filtered_links = filter(
      lambda s: s.find(name='div', class_='b_adurl') == None,
      links
    )
    links = list(
      map(lambda s: s.text, filtered_links)
    )

    search_result_items_zipped = list(
      zip(titles, links)
    )
    search_result_items = [
      SearchResultItem(title, link)
      for title, link in search_result_items_zipped
    ]

    return ScrapeResult(items=search_result_items)


  def _scrape_duckduckgo(self) -> ScrapeResult:
    return self._common_scrape(
        title_tag_name='a',
        title_class='result__a',
        link_tag_name='a',
        link_class='result__url'
    )


  def _scrape_ask(self) -> ScrapeResult:
    return self._common_scrape(
        title_tag_name='a',
        title_class='result-link',
        link_tag_name='p',
        link_class='PartialSearchResults-item-url'
    )


  def _scrape_mojeek(self) -> ScrapeResult:
    if self.soup.find(name='div', class_='results') == None:
      return ScrapeResult(items=[], no_results=True)

    else:
      return self._common_scrape(
          title_tag_name='a',
          title_class='ob',
          link_tag_name='p',
          link_class='i'
      )


  def _scrape_exalead(self) -> ScrapeResult:
    if self.soup.body.find(name='div', id='content').find(name='form') != None:
      return ScrapeResult(items=[], captcha=True)

    elif self.soup.body.find(name='div', id='noResults') != None:
      return ScrapeResult(items=[], no_results=True)

    else:
      return self._common_scrape(
          title_tag_name='a',
          title_class='title',
          link_tag_name='a',
          link_class='ellipsis'
      )


  def _scrape_lycos(self) -> ScrapeResult:
    return self._common_scrape(
      title_tag_name='a',
      title_class='result-link',
      link_tag_name='span',
      link_class='result-url'
    )


  def _scrape_yandex(self) -> ScrapeResult:
    if self.soup.find(name='div', class_='CheckboxCaptcha'):
      return ScrapeResult(items=[], captcha=True)

    return self._common_scrape(
      title_tag_name='div',
      title_class='organic__url-text',
      link_tag_name='a',
      link_class='Link_theme_outer'
    )


  def _scrape_swisscows(self) -> ScrapeResult:
    return self._common_scrape(
      title_tag_name='h2',
      title_class='title',
      link_tag_name='cite',
      link_class='site'
    )


  def _common_scrape(self, title_tag_name: str, title_class: str, link_tag_name: str, link_class: str) -> ScrapeResult:
    titles = self.soup.find_all(name=title_tag_name, class_=title_class)
    titles = list(
      map(lambda s: s.text, titles)
    )
  
    links = self.soup.find_all(name=link_tag_name, class_=link_class)
    links = list(
      map(lambda s: s.text, links)
    )

    search_result_items_zipped = list(
      zip(titles, links)
    )
    search_result_items = [
      SearchResultItem(title, link)
      for title, link in search_result_items_zipped
    ]

    return ScrapeResult(items=search_result_items)

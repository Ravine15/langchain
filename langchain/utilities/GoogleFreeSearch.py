import requests
from pydantic.class_validators import root_validator
from pydantic.main import BaseModel
from langchain.utils import get_from_dict_or_env
#from bs4 import BeautifulSoup
import cchardet
from pyquery import PyQuery as pq
from urllib.parse import parse_qs, quote_plus, urlparse


class GoogleSearchAPIWrapper(BaseModel):
    """Wrapper around the Serper.dev Google Search API.
    Example:
        .. code-block:: python

            from langchain import GoogleSearchAPIWrapper
            google_serper = GoogleSearchAPIWrapper()
    """
    k: int = 10
    gl: str = "us"
    hl: str = "en"
    type: str = "search"  # search, images, places, news
    tbs: Optional[str] = None
    aiosession: Optional[aiohttp.ClientSession] = None

    class Config:
        """Configuration for this pydantic object."""
        arbitrary_types_allowed = True   

    def results(self, query: str, **kwargs: Any) -> Dict:
        """Run query through GoogleSearch."""
        return self._google_search_results(
            query,
            gl=self.gl,
            hl=self.hl,
            num=self.k,
            tbs=self.tbs,
            search_type=self.type,
            **kwargs,
        )

    def run(self, query: str, **kwargs: Any) -> str:
        """Run query through GoogleSearch and parse result."""
        results = self._google_search_results(
            query,
            gl=self.gl,
            hl=self.hl,
            num=self.k,
            tbs=self.tbs,
            search_type=self.type,
            **kwargs,
        )

        return self._parse_results(results)

    async def aresults(self, query: str, **kwargs: Any) -> Dict:
        """Run query through GoogleSearch."""
        results = await self._google_search_results(
            query,
            gl=self.gl,
            hl=self.hl,
            num=self.k,
            search_type=self.type,
            tbs=self.tbs,
            **kwargs,
        )
        return results

    async def arun(self, query: str, **kwargs: Any) -> str:
        """Run query through GoogleSearch and parse result async."""
        results = await self._google_search_results(
            query,
            gl=self.gl,
            hl=self.hl,
            num=self.k,
            search_type=self.type,
            tbs=self.tbs,
            **kwargs,
        )

        return self._parse_results(results)

    def _parse_results(self, results: list) -> str:
        snippets = []
        L = self.k if self.k<len(results) else len(results)
        for r in results[0:L]:            
            snippets += r['text'].split("\n")[2:]
        return ' '.join(snippets)
        
    def _filter_link(self, link):    
        try:
            # Valid results are absolute URLs not pointing to a Google domain
            # like images.google.com or googleusercontent.com
            o = urlparse(link, "http")
            if o.netloc:
                return link
            # Decode hidden URLs.
            if link.startswith("/url?"):
                link = parse_qs(o.query)["q"][0]
                # Valid results are absolute URLs not pointing to a Google domain
                # like images.google.com or googleusercontent.com
                o = urlparse(link, "http")
                if o.netloc:
                    return link
        # Otherwise, or on error, return None.
        except Exception as e:
            return None
    def _google_search_results(
        self, search_term: str, search_type: str = "search", **kwargs: Any
    ) -> dict:
        url = "https://www.google.com/%s?hl=%s&q=%s&cr=%s" %(search_type, self.hl, search_term.replace(" ", "+"), self.gl)        
        r = requests.get(url)
        content = r.content
        charset = cchardet.detect(content)
        text = content.decode(charset["encoding"])    
        pq_content = pq(text) 
        #print(pq_content)
        search_results = []
        #import self.k(num)
        for p in pq_content.items("a"):
            if p.attr("href").startswith("/url?q="):
                pa = p.parent()
                if pa.is_("div"):
                    ppa = pa.parent()
                    if ppa.attr("class") is not None:
                        result = {}
                        result["title"] = p("h3").eq(0).text()
                        result["url_path"] = p("div").eq(1).text()
                        href = p.attr("href")
                        if href:
                            url = self._filter_link(href)
                            result["url"] = url
                        text = ppa("div").eq(0).text()
                        result["text"] = text
                        search_results.append(result)        
        return search_results
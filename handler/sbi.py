""" for SBI
"""
from selenium.webdriver.chrome.options import Options
import urllib
import pandas as pd
from bs4 import BeautifulSoup

from handler.handler import InvestmentTrustSiteHandler

class SBIHandler(InvestmentTrustSiteHandler):
    """ SBIHandler is a handler for SBI
    """
    
    __url_domestic = "https://site3.sbisec.co.jp/ETGate/?" + urllib.parse.urlencode({
        "_ControlID": "WPLETacR001Control",
        "_PageID": "DefaultPID",
        "_DataStoreID": "DSWPLETacR001Control",
        "_SeqNo": "1649728758632_default_task_354_DefaultPID_DefaultAID",
        "getFlg": "on",
        "_ActionID": "DefaultAID"
    })
    __url_foreign = "https://site3.sbisec.co.jp/ETGate/?" + urllib.parse.urlencode({
        "_ControlID" : "WPLETsmR001Control",
        "_DataStoreID" : "DSWPLETsmR001Control",
        "_PageID" : "WPLETsmR001Sdtl12",
        "sw_page" : "BondFx",
        "sw_param2" : "02_201",
        "cat1" : "home",
        "cat2" : "none",
        "getFlg" : "on"
    })
    __baseurl = "https://site3.sbisec.co.jp/ETGate/"
    
    def __init__(self, options=None):
        options = options or Options()
        options.headless = False
        
        super().__init__(
            self.__baseurl, 
            options=options
        )
        
        self.JPY = 0
        
        # login check
        html = self.browser.page_source
        soup = BeautifulSoup(html, 'html.parser')
        if soup.find(class_="login_title"):
            self.prompt_login()
    
    def prompt_login(self):
        input("Please login and press Key")
        
    def update(self):
        self.__update_domestic()
        self.__update_foreign()
    
    def __update_domestic(self):
        self.browser.get(self.__url_domestic)
        
        html = self.browser.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        res = soup.find_all(text="株式（現物/特定預り）")[0]
        res = res.find_parents("table")[0]

        df, = pd.read_html(str(res), header=[1])

        df1 = df[::2].copy()
        df1 = df1["保有株数"].str.split('\xa0', expand=True)
        df1 = df1.rename(columns={0: "ticker", 1: "name"})
        df1 = df1.reset_index()
        del df1["index"]

        df2 = df[1::2][["保有株数", "取得単価", "現在値"]].copy()
        df2 = df2.rename(columns={
            "保有株数": "amount", 
            "取得単価": "acquisition", 
            "現在値": "price"
        })
        df2 = df2.reset_index()
        del df2["index"]

        self.df_domestic = df1.join(df2)
        
        res = soup.find_all(text="買付余力")[0]
        res = res.find_parents("table")[0]

        df, _ = pd.read_html(str(res))

        self.JPY = df.iat[-1, -1]
    
    def __update_foreign(self):
        self.browser.get(self.__url_foreign)
        
        html = self.browser.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # US Stock
        res = soup.find_all(text="米国株式（現物/NISA預り）")[0]
        res = res.find_parents("table")[0]
        text = ""
        while len(text) == 0:
            res = res.next_sibling
            text = res.text.strip()
            
        df, = pd.read_html(str(res), header=[0])
        
        df1 = df[0::2]["保有数量"].copy()
        df1 = df1.str.split('\xa0', expand=True)
        df1 = df1.rename(columns={
            0: 'name', 
            1: 'ticker'
        })
        df1 = df1.reset_index()
        del df1["index"]
        
        df2 = df[1::2][['保有数量', '取得単価', '現在値']].copy()
        df2 = df2.rename(columns={
            '保有数量': 'amount',
            '取得単価': 'acquisition',
            '現在値': 'price',
        })
        df2 = df2.reset_index()
        del df2["index"]
        
        self.df_foreign = df1.join(df2)
                
        # Currency
        res = soup.find_all(text="参考為替レート")[0]
        res = res.find_parents("table")[0]

        df, = pd.read_html(str(res), header=[0])

        df1 = df[["参考為替レート", "参考為替レート.1"]].rename(columns={"参考為替レート": "name", "参考為替レート.1": "price"})
        df1["name"] = df1["name"].str.extract('(.+)/.+', expand=True)

        res = soup.find_all(text="買付余力")[0]
        res = res.find_parents("table")[0]

        df, = pd.read_html(str(res), header=[0])

        df2 = df[["|買付余力", "|買付余力.2"]].rename(columns={"|買付余力": "name", "|買付余力.2": "amount"})[:-1]
        df2[["name", "ticker"]] = df2["name"].str.extract('(.+)\((.+)\)', expand=True)

        df = pd.merge(df1, df2)

        new = pd.DataFrame([["円", 1, self.JPY, "JPY"]], columns=df.columns)
        df = pd.concat([df, new])
        df = df.reset_index()
        del df["index"]
        
        self.df_currency = df
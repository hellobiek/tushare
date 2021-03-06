# -*- coding:utf-8 -*-

"""
获取股票分类数据接口 
Created on 2015/02/01
@author: Jimmy Liu
@group : waditu
@contact: jimmysoa@sina.cn
"""

import pandas as pd
import datetime
from datetime import datetime
from bs4 import BeautifulSoup
from tushare.stock import cons as ct
from tushare.stock import ref_vars as rv
import json
import re
import random
from pandas.util.testing import _network_error_classes
import time
import tushare.stock.fundamental as fd
from tushare.util.netbase import Client

try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request


def get_industry_classified(standard='sina'):
    """
        获取行业分类数据
    Parameters
    ----------
    standard
    sina:新浪行业 sw：申万 行业
    
    Returns
    -------
    DataFrame
        code :股票代码
        name :股票名称
        c_name :行业名称
    """
    if standard == 'sw':
        df = _get_type_data(ct.SINA_INDUSTRY_INDEX_URL%(ct.P_TYPE['http'],
                                                    ct.DOMAINS['vsf'], ct.PAGES['ids_sw']))
    else:
        df = _get_type_data(ct.SINA_INDUSTRY_INDEX_URL%(ct.P_TYPE['http'],
                                                    ct.DOMAINS['vsf'], ct.PAGES['ids']))
    data = []
    ct._write_head()
    for row in df.values:
        rowDf =  _get_detail(row[0], retry_count=10, pause=0.01)
        rowDf['c_name'] = row[1]
        data.append(rowDf)
    data = pd.concat(data, ignore_index=True)
    return data
        

def get_concept_classified():
    """
        获取概念分类数据
    Return
    --------
    DataFrame
        code :股票代码
        name :股票名称
        c_name :概念名称
    """
    ct._write_head()
    df = _get_type_data(ct.SINA_CONCEPTS_INDEX_URL%(ct.P_TYPE['http'],
                                                    ct.DOMAINS['sf'], ct.PAGES['cpt']))
    data = []
    for row in df.values:
        rowDf =  _get_detail(row[0])
        if rowDf is not None:
            rowDf['c_name'] = row[1]
            data.append(rowDf)
    if len(data) > 0:
        data = pd.concat(data, ignore_index=True)
    return data


def get_area_classified():
    """
        获取地域分类数据
    Return
    --------
    DataFrame
        code :股票代码
        name :股票名称
        area :地域名称
    """
    df = fd.get_stock_basics()
    df = df[['name', 'area']]
    df.reset_index(inplace=True)
    df = df.sort_values('area').reset_index(drop=True)
    return df


def get_gem_classified():
    """
        获取创业板股票
    Return
    --------
    DataFrame
        code :股票代码
        name :股票名称
    """
    df = fd.get_stock_basics()
    df.reset_index(inplace=True)
    df = df[ct.FOR_CLASSIFY_B_COLS]
    df = df.ix[df.code.str[0] == '3']
    df = df.sort_values('code').reset_index(drop=True)
    return df
    

def get_sme_classified():
    """
        获取中小板股票
    Return
    --------
    DataFrame
        code :股票代码
        name :股票名称
    """
    df = fd.get_stock_basics()
    df.reset_index(inplace=True)
    df = df[ct.FOR_CLASSIFY_B_COLS]
    df = df.ix[df.code.str[0:3] == '002']
    df = df.sort_values('code').reset_index(drop=True)
    return df 

def get_st_classified():
    """
        获取风险警示板股票
    Return
    --------
    DataFrame
        code :股票代码
        name :股票名称
    """
    df = fd.get_stock_basics()
    df.reset_index(inplace=True)
    df = df[ct.FOR_CLASSIFY_B_COLS]
    df = df.ix[df.name.str.contains('ST')]
    df = df.sort_values('code').reset_index(drop=True)
    return df 


def _get_detail(tag, retry_count=3, pause=0.001):
    dfc = pd.DataFrame()
    p = 0
    num_limit = 100
    while(True):
        p = p+1
        for _ in range(retry_count):
            time.sleep(pause)
            try:
                ct._write_console()
                request = Request(ct.SINA_DATA_DETAIL_URL%(ct.P_TYPE['http'],
                                                                   ct.DOMAINS['vsf'], ct.PAGES['jv'],
                                                                   p,tag))
                text = urlopen(request, timeout=10).read()
                text = text.decode('gbk')
            except _network_error_classes:
                pass
            else:
                break
        reg = re.compile(r'\,(.*?)\:')
        text = reg.sub(r',"\1":', text)
        text = text.replace('"{symbol', '{"symbol')
        text = text.replace('{symbol', '{"symbol"')
        jstr = json.dumps(text)
        js = json.loads(jstr)
        df = pd.DataFrame(pd.read_json(js, dtype={'code':object}), columns=ct.THE_FIELDS)
        df = df[ct.FOR_CLASSIFY_B_COLS]
        dfc = pd.concat([dfc, df])
        if df.shape[0] < num_limit:
            return dfc
        #raise IOError(ct.NETWORK_URL_ERROR_MSG)

def _get_type_data(url):
    try:
        request = Request(url)
        data_str = urlopen(request, timeout=10).read()
        data_str = data_str.decode('GBK')
        data_str = data_str.split('=')[1]
        data_json = json.loads(data_str)
        df = pd.DataFrame([[row.split(',')[0], row.split(',')[1]] for row in data_json.values()],
                          columns=['tag', 'name'])
        return df
    except Exception as er:
        print(str(er))


def get_hs300s():
    """
    获取沪深300当前成份股及所占权重
    Return
    --------
    DataFrame
        code :股票代码
        name :股票名称
        date :日期
        weight:权重
    """
    from tushare.stock.fundamental import get_stock_basics
    try:
        wt = pd.read_excel(ct.HS300_CLASSIFY_URL_FTP%(ct.P_TYPE['ftp'], ct.DOMAINS['idxip'], 
                                                  ct.PAGES['hs300w']), parse_cols=[0, 3, 6])
        wt.columns = ct.FOR_CLASSIFY_W_COLS
        wt['code'] = wt['code'].map(lambda x :str(x).zfill(6))
        df = get_stock_basics()[['name']]
        df = df.reset_index()
        return pd.merge(df,wt)
    except Exception as er:
        print(str(er))


def get_sz50s():
    """
    获取上证50成份股
    Return
    --------
    DataFrame
        code :股票代码
        name :股票名称
    """
    try:
        df = pd.read_excel(ct.HS300_CLASSIFY_URL_FTP%(ct.P_TYPE['ftp'], ct.DOMAINS['idxip'], 
                                                  ct.PAGES['sz50b']), parse_cols=[0,1])
        df.columns = ct.FOR_CLASSIFY_B_COLS
        df['code'] = df['code'].map(lambda x :str(x).zfill(6))
        return df
    except Exception as er:
        print(str(er))      


def get_zz500s():
    """
    获取中证500成份股
    Return
    --------
    DataFrame
        code :股票代码
        name :股票名称
    """
    from tushare.stock.fundamental import get_stock_basics
    try:
        wt = pd.read_excel(ct.HS300_CLASSIFY_URL_FTP%(ct.P_TYPE['ftp'], ct.DOMAINS['idxip'], 
                                                   ct.PAGES['zz500wt']), parse_cols=[0, 3, 6])
        wt.columns = ct.FOR_CLASSIFY_W_COLS
        wt['code'] = wt['code'].map(lambda x :str(x).zfill(6))
        df = get_stock_basics()[['name']]
        df = df.reset_index()
        return pd.merge(df,wt)
    except Exception as er:
        print(str(er))

def get_index_constituent(index_name):
    """
    获取各种指数成份股
    输入：'sh'|'sz'|'hs300'|'sz50'|'zz500'|'cyb'
    Return
    --------
    DataFrame
        code :股票代码
        name :股票名称
    """
    try:
        if index_name == 'sh' or index_name == 'hs300' or index_name == 'sz50' or index_name == 'zz500':
            url = ct.SZ_CLASSIFY_URL_FTP%(ct.P_TYPE['http'],ct.DOMAINS['idx'],ct.PAGES[index_name])
            ucols = [4, 5]
        else:
            url = ct.SZSE_CLASSIFY_URL_HTTP%(ct.P_TYPE['http'],ct.DOMAINS['szse'],ct.PAGES[index_name])
            ucols = [0, 1]
        wt = pd.read_excel(url, usecols=ucols)
        wt.columns = ct.FOR_CLASSIFY_COLS
        wt['code'] = wt['code'].map(lambda x :str(x).zfill(6))
        return wt
    except Exception as er:
        print(str(er)) 
        return None

def get_terminated(markets = ['sz', 'sh']):
    """
    获取终止上市股票列表
    Return
    --------
    DataFrame
        code :股票代码
        name :股票名称
        oDate:上市日期
        tDate:终止上市日期
    """
    try:
        res = None
        for market in markets:
            if market == 'sh':
                ref = ct.SSEQ_CQ_REF_URL%(ct.P_TYPE['http'], ct.DOMAINS['sse'])
                clt = Client(rv.TERMINATED_URL%(ct.P_TYPE['http'], ct.DOMAINS['sseq'],
                                                ct.PAGES['ssecq'], _random(5),
                                                _random()), ref=ref, cookie=rv.MAR_SH_COOKIESTR)
                lines = clt.gvalue()
                lines = lines.decode('utf-8') if ct.PY3 else lines
                lines = lines[19:-1]
                lines = json.loads(lines)
                df = pd.DataFrame(lines['result'], columns=rv.TERMINATED_T_COLS)
            else:
                url = "http://www.szse.cn/szseWeb/ShowReport.szse?SHOWTYPE=xlsx&CATALOGID=1793_ssgs&ENCODE=1&TABKEY=tab2"
                df = pd.read_excel(url, usecols=[0, 1, 2, 3])
            df.columns = rv.TERMINATED_COLS
            df['code'] = df['code'].map(lambda x :str(x).zfill(6))
            res = df if res is None else res.append(df)
        return res.reset_index(drop = True)
    except Exception as er:
        print(str(er))
        return None

def parse_jsonp(jsonp_str):
    try:
        return re.search('^[^(]*?\((.*)\)[^)]*$', jsonp_str).group(1)
    except:
        raise ValueError('Invalid JSONP')

def get_halted(markets = ['sz', 'sh']):
    """
    获取当天停牌的个股
    Input
        markets = ['sz', 'sh'] default is both sh and sz
    Return
    --------
    DataFrame
        code : 股票代码
        market : 证券交易所
        name : 股票名称
        stopReason : 终止上市日期
    """
    try:
        res = None
        today = datetime.now().strftime('%Y-%m-%d')
        for market in markets:
            if market == 'sh':
                url = rv.HALTED_SH_URL%(ct.P_TYPE['http'], ct.DOMAINS['sseq'], ct.PAGES['infodis'], ct.PAGES['ssesppq'], _random(5), today, _random())
                ref = ct.SSEQ_CQ_REF_URL%(ct.P_TYPE['http'], ct.DOMAINS['sse'])
                clt = Client(url, ref=ref, cookie=rv.MAR_SH_COOKIESTR)
                lines = clt.gvalue()
                lines = lines.decode('utf-8')
                lines = json.loads(parse_jsonp(lines))
                df = pd.DataFrame(lines['pageHelp']['data'], columns=rv.HALTED_T_COLS)
                df = df[['productCode', 'productName', 'showDate', 'stopDate', 'stopReason', 'stopTime']]
                df.columns = rv.HALTED_COLS_SH
            else:
                url = "http://www.szse.cn/api/report/ShowReport/data?SHOWTYPE=JSON&CATALOGID=1798&TABKEY=tab1&txtKsrq=%s&txtZzrq=%s&txtKsrq-txtZzrq=%s&random=%s" % (today, today, today, random.random())
                html = urlopen(url).read()
                html = html.decode('utf-8')
                html_data = json.loads(html)
                obj_list = html_data[0]['data']
                page_num = html_data[0]['metadata']['pagecount']
                if 0 == page_num: continue
                for page_index in range(page_num - 1):
                    url = "http://www.szse.cn/api/report/ShowReport/data?SHOWTYPE=JSON&CATALOGID=1798&TABKEY=tab1&PAGENO=%s&txtKsrq=%s&txtZzrq=%s&txtKsrq-txtZzrq=%s&random=%s" % (page_index + 2, today, today, today, random.random())
                    html = urlopen(url).read()
                    html = html.decode('utf-8')
                    html_data = json.loads(html)
                    tmp_list = html_data[0]['data']
                    obj_list.extend(tmp_list)
                df = pd.DataFrame(obj_list)
                df.columns = rv.HALTED_COLS_SZ
            df['market'] = market
            res = df if res is None else res.append(df)
        return res.reset_index(drop = 'True')
    except Exception as er:
        print(str(er))
        return None

def get_suspended(markets = ['sz', 'sh']):
    """
    获取暂停上市股票列表
    Return
    --------
    DataFrame
        code :股票代码
        name :股票名称
        oDate:上市日期
        tDate:终止上市日期
    """
    try:
        res = None
        for market in markets:
            if market == 'sh':
                ref = ct.SSEQ_CQ_REF_URL%(ct.P_TYPE['http'], ct.DOMAINS['sse'])
                clt = Client(rv.SUSPENDED_URL%(ct.P_TYPE['http'], ct.DOMAINS['sseq'],
                                            ct.PAGES['ssecq'], _random(5),
                                            _random()), ref=ref, cookie=rv.MAR_SH_COOKIESTR)
                lines = clt.gvalue()
                lines = lines.decode('utf-8') if ct.PY3 else lines
                lines = lines[19:-1]
                lines = json.loads(lines)
                df = pd.DataFrame(lines['result'], columns=rv.TERMINATED_T_COLS)
            else:
                url = "http://www.szse.cn/szseWeb/ShowReport.szse?SHOWTYPE=xlsx&CATALOGID=1793_ssgs&ENCODE=1&TABKEY=tab1"
                df = pd.read_excel(url, usecols=[0, 1, 2, 3])
            df.columns = rv.TERMINATED_COLS
            df['code'] = df['code'].map(lambda x :str(x).zfill(6))
            res = df if res is None else res.append(df)
        return res.reset_index(drop = True)
    except Exception as er:
        print(str(er))
        return None

def _random(n=13):
    from random import randint
    start = 10**(n-1)
    end = (10**n)-1
    return str(randint(start, end))

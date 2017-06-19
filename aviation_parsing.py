#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Mon May 29 11:29:25 2017

@author: BennyBluebird
"""

from bs4 import BeautifulSoup
import pandas as pd
import requests

datadir = "."

def extract_data(airline, airport):
    
    session_data = {"event_validation": "",
            "view_state": "",
            "view_state_generator": ""}
    
    session = requests.Session()
    r = session.get("https://www.transtats.bts.gov/Data_Elements.aspx?%2fData=2")
    
    soup = BeautifulSoup(r.text, 'lxml')
    ev = soup.find(id="__EVENTVALIDATION")
    session_data["event_validation"] = ev["value"]
        
    vs = soup.find(id="__VIEWSTATE")
    session_data["view_state"] = vs["value"]
        
    vsg = soup.find(id="__VIEWSTATEGENERATOR")
    session_data["view_state_generator"] = vsg["value"]
    
    event_validation = session_data["event_validation"]
    view_state = session_data["view_state"]
    view_state_generator = session_data["view_state_generator"]
    
    r = session.post("https://www.transtats.bts.gov/Data_Elements.aspx?Data=2",
                      data = (
                              ("__EVENTTARGET", ""),
                              ("__EVENTARGUMENT", ""),
                              ("__VIEWSTATE", view_state),
                              ("__EVENTVALIDATION", event_validation),
                              ("__VIEWSTATEGENERATOR", view_state_generator),
                              ("CarrierList", airline),
                              ("AirportList", airport),
                              ("Submit", "Submit")
                              ))
    
    return r.text


def extract_data_to_json(airline, airport, international=False):
    
    request_data = extract_data(airline, airport)
    
    data = []
    info = {}
    info["courier"], info["airport"] = airline, airport
    rows = []
    
    soup = BeautifulSoup(request_data, 'lxml')
    datagrid = soup.find(id='DataGrid1')
    for tr in datagrid.find_all('tr'):
        columns = []
        for td in tr.find_all('td'):
            columns.append(td.text)
        rows.append(columns)
    
    for row in rows[1:]:
        if row[1] != 'TOTAL':
            row_dict = {'flights':{}}
            row_dict['airport'] = info['airport']
            row_dict['courier'] = info['courier']
            row_dict['year'] = int(row[0])
            row_dict['month'] = int(row[1])
            try:
                row_dict['flights']['domestic'] = int(row[2].replace(',', ''))
            except ValueError:
                row_dict['flights']['domestic'] = 'NaN'
            if international:
                try:
                    row_dict['flights']['international'] = int(row[3].replace(',', ''))
                except ValueError:
                    row_dict['flights']['international'] = 'NaN'
            data.append(row_dict)

    return data


def process_html_to_csv(f):
    
    pass


        
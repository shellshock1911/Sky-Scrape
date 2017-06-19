#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Mon May 29 11:29:25 2017

@author: BennyBluebird
"""

from bs4 import BeautifulSoup
from datetime import datetime
import numpy as np
import pandas as pd
import requests
import json

datadir = "."

def _extract_data(airline, airport):
    
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


def _parse_request(request_data):
    
    rows = []
    
    soup = BeautifulSoup(request_data, 'lxml')
    datagrid = soup.find(id='DataGrid1')
    for tr in datagrid.find_all('tr'):
        columns = []
        for td in tr.find_all('td'):
            columns.append(td.text)
        rows.append(columns)
    
    return rows


def extract_data_to_json(airline, airport, international=False):
    
    request_data = _extract_data(airline, airport)
    
    data = []
    info = {}
    info["courier"], info["airport"] = airline, airport
    
    rows = _parse_request(request_data)
    rows = rows[1:]
    
    for row in rows[1:]:
        year, month, domestic, international, _ = row
        if month == 'TOTAL':
            continue
        row_dict = {'flights':{}}
        row_dict['airport'] = info['airport']
        row_dict['courier'] = info['courier']
        row_dict['year'] = int(year)
        row_dict['month'] = int(month)
        try:
            row_dict['flights']['domestic'] = int(domestic.replace(',', ''))
        except ValueError:
            row_dict['flights']['domestic'] = np.nan
        if international:
            try:
                row_dict['flights']['international'] = int(international.replace(',', ''))
            except ValueError:
                row_dict['flights']['international'] = np.nan
        data.append(row_dict)

    with open('{}-{}.json'.format(airline, airport), 'w') as outfile:
        json.dump(data, outfile, indent=4, sort_keys=True)


def extract_data_to_csv(airline, airport, international=False):
    
    request_data = _extract_data(airline, airport)
    indexes = []
    if international:
        prep_dict = {'Domestic': list(), 'International': list()}
    else:
        prep_dict = {'Domestic': list()}
    
    rows = _parse_request(request_data)
    rows = rows[1:]
        
    for row in rows[1:]:
        year, month, domestic, international, _ = row
        if month == 'TOTAL':
            continue
        timestring = '{}-{}'.format(year, month)
        index = datetime.strptime(timestring, '%Y-%m')
        indexes.append(index)
        try:
            prep_dict['Domestic'].append(int(domestic.replace(',', '')))
        except ValueError:
            prep_dict['Domestic'].append(np.nan)
        if international:
            try:
                prep_dict['International'].append(int(international.replace(',', '')))
            except ValueError:
                prep_dict['International'].append(np.nan)
    
    df = pd.DataFrame(prep_dict, index=indexes)
    
    with open('{}-{}.csv'.format(airline, airport), 'w') as outfile:
        df.to_csv(outfile, index_label='Date')
    
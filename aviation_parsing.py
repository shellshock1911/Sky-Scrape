#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
from datetime import datetime
import json
import numpy as np
import pandas as pd
import pickle
import os
import requests

datadir = "aviation_data"

def _extract_html(airline, airport, additional_requests=None):
    
    session = requests.Session()
    get_request = session.get("https://www.transtats.bts.gov/Data_Elements.aspx?%2fData=2")
    
    soup = BeautifulSoup(get_request.text, 'lxml')
    event_validation = soup.find(id="__EVENTVALIDATION")['value']
    view_state = soup.find(id="__VIEWSTATE")['value']
    view_state_generator = soup.find(id="__VIEWSTATEGENERATOR")['value']
    
    html_requests = []
        
    passengers_request = session.post("https://www.transtats.bts.gov/Data_Elements.aspx?Data=2",
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
    
    html_requests.append(passengers_request.text)
    
    if additional_requests:
        for request in additional_requests:
            request = session.post("https://www.transtats.bts.gov/Data_Elements.aspx?Data=2",
                      data = (
                              ("__EVENTTARGET", "Link_{}".format(request)),
                              ("__EVENTARGUMENT", ""),
                              ("__VIEWSTATE", view_state),
                              ("__EVENTVALIDATION", event_validation),
                              ("__VIEWSTATEGENERATOR", view_state_generator),
                              ("CarrierList", airline),
                              ("AirportList", airport),
                              ))
        
            html_requests.append(request.text)
    
    return html_requests


def _parse_html_request(html_request):
    
    rows = []
    
    soup = BeautifulSoup(html_request, 'lxml')
    datagrid = soup.find(id='DataGrid1')
    for tr in datagrid.find_all('tr'):
        columns = []
        for td in tr.find_all('td'):
            columns.append(td.text)
        rows.append(columns)
        
    rows = rows[1:]
    for row in rows:
        year, month, domestic, international, _ = row
        if month == 'TOTAL':
            rows.remove(row)
    
    return rows

def get_airlines():
    
    with open('pkl_objects/airlines.pkl', 'rb') as pkl:
        airlines = pickle.load(pkl)
        
    return airlines

def get_airports():
    
    with open('pkl_objects/airports.pkl', 'rb') as pkl:
        airports = pickle.load(pkl)
        
    return airports
        
def get_combinations():
    
    with open('pkl_objects/combinations.pkl', 'rb') as pkl:
        combinations = pickle.load(pkl)
        
    return combinations
    
def extract_data_to_json(airline, airport, international=False, create_file=False):
    
    html_requests = _extract_html(airline, airport)
    
    data = []
    info = {}
    info["courier"], info["airport"] = airline, airport
    
    rows = _parse_html_request(html_requests)
    
    for row in rows:
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

    if create_file:
        with open(datadir + '/{}-{}.json'.format(airline, airport), 'w') as outfile:
            json.dump(data, outfile, indent=4, sort_keys=True)
            
    return data


def _parse_indexes(rows):
    
    indexes = []
    
    for row in rows:
        year, month, domestic, international, _ = row
        timestring = '{}-{}'.format(year, month)
        index = datetime.strptime(timestring, '%Y-%m')
        indexes.append(index)
        
    return indexes

def _parse_data(rows, label, international=False):
    
    if international:
        prep_dict = {'{}_Domestic'.format(label): list(), '{}_International'.format(label): list()}
    else:
        prep_dict = {'{}_Domestic'.format(label): list()}
    
    for row in rows:
        _, _, domestic_data, international_data, _ = row
        try:
            prep_dict['{}_Domestic'.format(label)].append(int(domestic_data.replace(',', '')))
        except ValueError:
            prep_dict['{}_Domestic'.format(label)].append(np.nan)
        if international:
            try:
                prep_dict['{}_International'.format(label)].append(int(international_data.replace(',', '')))
            except ValueError:
                prep_dict['{}_International'.format(label)].append(np.nan)
    
    return prep_dict


def extract_data_to_csv(airline, airport, additional_requests=None, international=False, create_file=False):
    
    airlines = get_airlines()
    if airline not in airlines:
        raise ValueError(airline + " is an invalid airline code. Run get_airlines() in an interpreter"
                         "for a full list of valid airline codes.")
    
    
    airports = get_airports()
    if airport not in airports:
        raise ValueError(airport + " is an invalid airport code. Run get_airports() in an interpreter"
                         "for a full list of valid airport codes.")
        
    html_requests = _extract_html(airline, airport, additional_requests)
    passenger_rows = _parse_html_request(html_requests[0])
    indexes = _parse_indexes(passenger_rows)
    parsed_data = _parse_data(passenger_rows, 'Passengers', international)
    
    if additional_requests:
        possible_additional = ["Flights", "RPM", "ASM"]
        if any(item not in possible_additional for item in additional_requests):
            raise ValueError("additional_requests includes an invalid value. Possible values include:"
                " 'Flights', 'RPM', 'ASM'. Must be passed as a list.")
        for i, request in enumerate(additional_requests):
            rows = _parse_html_request(html_requests[i + 1])
            parsed_rows = _parse_data(rows, request, international)
            parsed_data.update(parsed_rows)
    
    df = pd.DataFrame(parsed_data, index=indexes)
    
    if create_file:
        if not os.path.isdir(datadir):
            os.mkdir(datadir)
        with open(datadir + '/{}-{}.csv'.format(airline, airport), 'w') as outfile:
            df.to_csv(outfile, index_label='Date')
        return None
    
    return df
    
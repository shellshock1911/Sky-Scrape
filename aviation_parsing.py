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
    
    # Helper function that extracts one or more raw html files from the Department 
    # of Transportation source and stores them in a list of strings. Should not 
    # be called directly.
    
    # Fetches and stores data to be used in later requests
    
    session = requests.Session()
    get_request = session.get("https://www.transtats.bts.gov/Data_Elements.aspx?%2fData=2")
    
    soup = BeautifulSoup(get_request.text, 'lxml')
    event_validation = soup.find(id="__EVENTVALIDATION")['value']
    view_state = soup.find(id="__VIEWSTATE")['value']
    view_state_generator = soup.find(id="__VIEWSTATEGENERATOR")['value']
    
    # Passenger data is requested by default. This and data on all additional
    # requests is stored in a list. At this point the data is still in raw
    # html format and not easily readable.
    
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
    
    # Helper function that extracts and cleans data from a single raw html file, 
    # returning an array of rows, each containing a year, month, domestic value, 
    # international value, and total value for desired aviation metric. Should 
    # not be called directly.
    
    
    rows = []
    
    soup = BeautifulSoup(html_request, 'lxml')
    datagrid = soup.find(id='DataGrid1')
    for tr in datagrid.find_all('tr'):
        columns = []
        for td in tr.find_all('td'):
            columns.append(td.text)
        rows.append(columns)
        
    rows = rows[1:] # Skips header information
    for row in rows:
        year, month, domestic, international, _ = row # Total data is not necessary
        if month == 'TOTAL': # Skips over rows that serve as annual sums
            rows.remove(row)
    
    return rows

def get_airlines():
    
    """Returns a list of all possible airline codes that can be later passed
    as arguments to extract_data_to_json or extract_data_to_csv. Must be called 
    from Flight-Forecast top-level directory.
    
    """
    
    with open('pkl_objects/airlines.pkl', 'rb') as pkl:
        airlines = pickle.load(pkl)
        
    return airlines

def get_airports():
    
    """Returns a list of all possible airport codes that can be later passed
    as arguments to extract_data_to_json or extract_data_to_csv. Must be called 
    from Flight-Forecast top-level directory.
    
    """
    
    with open('pkl_objects/airports.pkl', 'rb') as pkl:
        airports = pickle.load(pkl)
        
    return airports
        
def get_combinations():
    
    """Returns a list of all possible airline-airport codes that could be used
    with a user-defined looping function to create many JSON or CSV files.
    
    """
    
    with open('pkl_objects/combinations.pkl', 'rb') as pkl:
        combinations = pickle.load(pkl)
        
    return combinations
    
def extract_data_to_json(airline, airport, international=False, create_file=False):
    
    """Takes an airline code and an airport code as arguments and creates a JSON 
    file containing monthly passenger data for all years for which the data exists. 
    Data is interpreted as the number of passengers that originate from the 
    desired airport. A list of JSON objects can be assigned to a variable instead 
    of creating a CSV file by passing create_file=False. Should be run from
    the Flight-Forecast top-level directory.
    
    Optional parameters allow for the addition of international data
    as well as receiving data on flights, revenue passenger-miles, and available seat-miles. 
    Pass one or more of "Flights", "RPM", and "ASM" in a list to additional_requests
    parameter to request this data. 
    
    Note that runtime depends on user's connection speed as well as number
    of requests passed. Because each request must be processed individually, all 
    else held equal, runtime is O(number of requests).
    
    """
    
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
    
    # Helper function that extracts datetime strings from aviation data array
    # and transforms into datetime objects to be used in assembling CSV file. 
    # Should not be called directly.
    
    indexes = []
    
    # Year and month are initially stored in two separate columns.
    # This reduces the storage to one column that holds datetime objects.
    
    for row in rows:
        year, month, domestic, international, _ = row
        timestring = '{}-{}'.format(year, month)
        index = datetime.strptime(timestring, '%Y-%m')
        indexes.append(index)
        
    return indexes

def _parse_data(rows, label, international=False):
    
    # Helper function that extracts domestic metric data from aviation data
    # array for later use in assembling CSV file. Missing data takes NaN label.
    # Should not be called directly.
    
    if international:
        prep_dict = {'{}_Domestic'.format(label): list(), '{}_International'.format(label): list()}
    else:
        prep_dict = {'{}_Domestic'.format(label): list()}
        
    # Input values are read in as strings and can include commas to separate place (e.g. 400,231).
    # Output values are stored as integers and no longer contain commas.
    
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


def extract_data_to_csv(airline, airport, additional_requests=None, international=False, create_file=True):
    
    """Takes an airline code and an airport code as arguments and creates a CSV 
    file containing monthly passenger data for all years for which the data exists. 
    Data is interpreted as the number of passengers that originate from the 
    desired airport. A pandas DataFrame can be assigned to a variable instead 
    of creating a CSV file by passing create_file=False. Should be run from
    the Flight-Forecast top-level directory. Run get_airlines() or get_airports()
    for full lists of valid codes.
    
    Optional parameters allow for the addition of international data
    as well as receiving data on flights, revenue passenger-miles, and available seat-miles. 
    Pass one or more of "Flights", "RPM", and "ASM" in a list to the additional_requests
    parameter to request this data. 
    
    Note that runtime depends on user's connection speed as well as number
    of requests passed. Because each request must be processed individually, all 
    else held equal, runtime is O(n_requests).
    
    """
    
    airlines = get_airlines()
    if airline not in airlines:
        raise ValueError(airline + " is an invalid airline code. Run get_airlines()" 
            " in an interpreter for a full list of valid airline codes.")
    
    
    airports = get_airports()
    if airport not in airports:
        raise ValueError(airport + " is an invalid airport code. Run get_airports()" 
            " in an interpreter for a full list of valid airport codes.")
    
    # This section of the function begins creating the data dictionary used
    # to build the CSV file. Initially, only passenger data is included.
    # The keys are metrics and the values are lists of quantities - one for each 
    # month in the dataset.
    
    html_requests = _extract_html(airline, airport, additional_requests)
    passenger_rows = _parse_html_request(html_requests[0]) # Parsing raw passenger html
    indexes = _parse_indexes(passenger_rows) # One time datetime index creation
    parsed_data = _parse_data(passenger_rows, 'Passengers', international) 
    
    # If the user requests data on additional metrics, the data dictionary
    # can be updated with these metrics as keys and lists of quantities as values.
    
    if additional_requests:
        possible_additional = ["Flights", "RPM", "ASM"]
        if any(item not in possible_additional for item in additional_requests):
            raise ValueError("additional_requests includes an invalid value." 
                " Possible values include: 'Flights', 'RPM', 'ASM'." 
                " Values must be passed in a list.")
        for i, request in enumerate(additional_requests):
            rows = _parse_html_request(html_requests[i + 1]) # Skips raw passenger html
            parsed_rows = _parse_data(rows, request, international)
            parsed_data.update(parsed_rows)
    
    # Any NaN fields in the international column cause the data type for all fields
    # in the column to become float32. This is reverted to int32 below.
    
    df = pd.DataFrame(parsed_data, index=indexes, dtype=np.int32)
    
    # This call will overwrite the existing file if it already exists in
    # the aviation_data directory.
    
    if create_file:
        if not os.path.isdir(datadir):
            os.mkdir(datadir)
        with open(datadir + '/{}-{}.csv'.format(airline, airport), 'w') as outfile:
            df.to_csv(outfile, index_label='Date')
        return None
    
    return df



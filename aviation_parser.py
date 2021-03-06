#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import sys
import time
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from utilities import get_airlines, get_airports

AIRLINE = sys.argv[1]
AIRPORT = sys.argv[2]
DATADIR = "aviation_data"
CODEDICT = {
            'All': 'All',
            'AS': 'Alaska_Airlines',
            'G4': 'Allegient_Air',
            'AA': 'American_Airlines',
            '5Y': 'Atlas_Air',
            'DL': 'Delta_Airlines',
            'MQ': 'Envoy_Air',
            'EV': 'ExpressJet',
            'F9': 'Frontier_Airlines',
            'HA': 'Hawaiian_Airlines',
            'B6': 'JetBlue_Airways',
            'OO': 'SkyWest_Airlines',
            'WN': 'Southwest_Airlines',
            'NK': 'Spirit_Airlines',
            'UA': 'United_Airlines',
            'VX': 'Virgin_America'
           }

FULL_NAME = CODEDICT[AIRLINE]


def _extract_html(airline, airport, additional_requests=None):
    
    # Step 1
    
    # Helper function that extracts one or more raw html files from the Department 
    # of Transportation source and stores them in a list of strings. 
    # Should not be called directly.
    
    # Fetches and stores session and state data to be used in later requests
    
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
                                      data=(
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
    
    # After the passenger request is made, additional requests can be made
    # from that point by linking them in __EVENTTARGET below.
    
    if additional_requests:
        for request in additional_requests:
            request = session.post("https://www.transtats.bts.gov/Data_Elements.aspx?Data=2",
                                   data=(
                                       ("__EVENTTARGET", "Link_{}".format(request)),
                                       ("__EVENTARGUMENT", ""),
                                       ("__VIEWSTATE", view_state),
                                       ("__EVENTVALIDATION", event_validation),
                                       ("__VIEWSTATEGENERATOR", view_state_generator),
                                       ("CarrierList", airline),
                                       ("AirportList", airport)
                                       ))
        
            html_requests.append(request.text)
    
    return html_requests


def _parse_html_request(html_request):
    
    # Step 2
    
    # Helper function that extracts and cleans data from a single raw html file, 
    # returning an array of rows, each containing a year, month, domestic value, 
    # international value, and total value for desired aviation metric. 
    # Should not be called directly.
    
    rows = []
    
    soup = BeautifulSoup(html_request, 'lxml')
    datagrid = soup.find(id='DataGrid1')
    
    try:
        for row in datagrid.find_all('tr'):
            columns = []
            for field in row.find_all('td'):
                columns.append(field.text)
            rows.append(columns)
        
    except AttributeError:
        raise Exception("No data exists for this query. Please try a different combination.")
        
    rows = rows[1:] # Skips header information
    for row in rows:
        _, month, _, _, _ = row
        if month == 'TOTAL': # Skips over rows that serve as annual sums
            rows.remove(row)
    
    return rows
    

def _parse_indexes(rows):
    
    # Step 3
    
    # Helper function that extracts datetime strings from aviation data array
    # and transforms into datetime objects to be used in assembling CSV file. 
    # Should not be called directly.
    
    indexes = []
    
    # Year and month strings are initially stored in separate columns.
    # This consolidates them into one column that holds datetime objects.
    
    for row in rows:
        year, month, _, _, _ = row
        timestring = '{}-{}'.format(year, month)
        index = datetime.strptime(timestring, '%Y-%m')
        indexes.append(index)
        
    return indexes


def _parse_data(rows, label, international=False):
    
    # Step 4
    
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
            prep_dict['{}_Domestic'.format(label)].append(
                int(domestic_data.replace(',', '')))
        except ValueError:
            prep_dict['{}_Domestic'.format(label)].append(np.nan)
        if international:
            try:
                prep_dict['{}_International'.format(label)].append(
                    int(international_data.replace(',', '')))
            except ValueError:
                prep_dict['{}_International'.format(label)].append(np.nan)
    
    return prep_dict


def extract_data_to_csv(airline, airport, international=True, 
                        additional_requests=['Flights', 'ASM', 'RPM']):
    
    """Takes an airline code and an airport code as arguments and creates a CSV 
    file on disk containing monthly passenger data for all months for which the data exists. 
    Data is interpreted as originating from the desired airport. Should be run from 
    the Flight-Forecast top-level directory. Run get_airlines() or get_airports() 
    for full lists of valid input codes.
    
    Optional parameters allow for the addition of international data
    as well as receiving data on flights, revenue passenger-miles, and available seat-miles. 
    Pass one or more of "Flights", "RPM", and "ASM" in a list to the additional_requests
    parameter to request this data. All of these are included by default.
    
    Note that runtime depends on connection speed as well as number
    of requests passed. Because each request must be processed individually, all 
    else held equal, runtime is O(n_requests).
    
    """
    start = time.time()

    airlines = get_airlines()
    if airline not in airlines:
        raise ValueError(airline + " is an invalid airline code. Run get_airlines() from utilities.py" 
                                   " in an interpreter for a full list of valid airline codes.")

    airports = get_airports()
    if airport not in airports:
        raise ValueError(airport + " is an invalid airport code. Run get_airports() from utilities.py" 
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
    
    # Any NaN fields in the international column causes the data type for all fields
    # to become float32. This is coerced to int32.
    
    dataframe = pd.DataFrame(parsed_data, index=indexes, dtype=np.int32)
    
    # File will be overwritten if it already exists in the aviation_data directory.
    
    if not os.path.isdir(DATADIR + '/{}'.format(FULL_NAME)):
        os.mkdir(DATADIR + '/{}'.format(FULL_NAME))
    with open(DATADIR + '/{0}/{1}-{2}.csv'.format(FULL_NAME, airline, airport), 'w') as outfile:
        dataframe.to_csv(outfile, index_label='Date')
        end = time.time()
        print "Requests completed in", round((end - start), 2), "seconds"
        print "Data available at: " + os.path.join(os.path.dirname(__file__), outfile.name)
    return None

if __name__ == '__main__':
    extract_data_to_csv(AIRLINE, AIRPORT)



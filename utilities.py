#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 26 17:17:13 2017

@author: BennyBluebird
"""

def get_airlines():
    
    """Returns a list of all possible airline codes that can be later passed
    as arguments to extract_data_to_json or extract_data_to_csv. Must be called 
    from Flight-Forecast top-level directory.
    
    """
    
    airlines = ['All', 'AS', 'G4', 'AA', '5Y', 'DL', 'MQ', 'EV', 'F9', 'HA', 'B6', 'OO',
                'WN', 'NK', 'UA', 'VX']
        
    return airlines

def get_airports():
    
    """Returns a list of all possible airport codes that can be later passed
    as arguments to extract_data_to_json or extract_data_to_csv. Must be called 
    from Flight-Forecast top-level directory.
    
    """
    
    airports = ['All', 'ATL', 'BWI', 'BOS', 'CLT', 'MDW', 'ORD', 'DAL', 'DFW', 'DEN', 
                'DTW', 'FLL', 'IAH', 'LAS', 'LAX', 'MIA', 'MSP', 'JFK', 'LGA', 
                'EWR', 'MCO', 'PHL', 'PHX', 'PDX', 'SLC', 'SAN', 'SFO', 'SEA', 
                'TPA', 'DCA', 'IAD']
        
    return airports
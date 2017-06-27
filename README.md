# Sky Scrape

This tool can be used to easily pull data on a variety of aviation metrics that the U.S. Department of Transportation makes available each month at [TranStats](https://www.transtats.bts.gov/Data_Elements.aspx). The source is built in ASP.NET, making it particularly cumbersome to access the data in a convenient and efficient manner. There is no mechanism provided for downloading the data to common data storage formats such as CSV or JSON. Using this can bridge that gap by making the the desired requests automatically, scraping the relevant data, and storing it in a CSV file on disk.

To be used directly from your command line, as such:

```
python aviation_parser.py DL ATL
```

This will fetch monthly data on all Delta Airlines flights originating from Hartsfield-Jackson Atlanta International Airport and parse it to a file named `DL-ATL.csv` in the `aviation_metrics` directory. By default, data on number of passengers, number of flights, revenue passenger-miles\*, and available seat-miles\*\* is extracted for both domestic and international flights for each month from October 2002 to the month three months prior to the current month. As of June 2017, data is available up to March 2017.

Airline and airport arguments are not flexible, must be all caps, and adhere precisely to [IATA codes](https://en.wikipedia.org/wiki/International_Air_Transport_Association_code). See below for full lists of codes and/or search one [here](http://www.iata.org/publications/Pages/code-search.aspx) that you unsure about. Note that although there are 15 airlines and 30 airports to choose from, not all combinations will necessarily return complete data or even any data at all. This is due to the fact that a particular airline may not operate at a certain airport. For example, Virgin American (VX) does not serve Atlanta (ATL). If this occurs or if an invalid code is passed to the parser, descriptive errors will be raised with instructions on how to proceed.

I've included three [example datasets](https://github.com/shellshock1911/Sky-Scrape/tree/master/aviation_data) to demonstrate the kind of output that can be expected. Possible use cases could include descriptive analysis and/or [visualization](https://github.com/shellshock1911/Sky-Scrape/blob/master/images/dl-atl.jpg), or for use in the forecasting of a particular time series. Be aware the that runtime of the program is largely dependent on your connection speed, so please be patient if it doesn't complete immediately. Normal usage should require no more than 60 seconds.

-----------

**Valid airline codes**: 'AS', 'G4', 'AA', '5Y', 'DL', 'MQ', 'EV', 'F9', 'HA', 'B6', 'OO', 'WN', 'NK', 'UA', 'VX'

**Valid airport codes**: 'ATL', 'BWI', 'BOS', 'CLT', 'MDW', 'ORD', 'DAL', 'DFW', 'DEN', 'DTW', 'FLL', 'IAH', 'LAS', 'LAX', 'MIA', 'MSP', 'JFK', 'LGA', 'EWR', 'MCO', 'PHL', 'PHX', 'PDX', 'SLC', 'SAN', 'SFO', 'SEA', 'TPA', 'DCA', 'IAD'

-----------

\* *Number of miles flown by billed passengers. Reported in millions.*

\*\* *Number of miles flown by available seat capacity. Reported in millions.*




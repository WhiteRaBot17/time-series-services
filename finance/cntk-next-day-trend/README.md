[issue-template]: ../../../../../issues/new?template=BUG_REPORT.md
[feature-template]: ../../../../../issues/new?template=FEATURE_REQUEST.md

![singnetlogo](../../../docs/assets/singnet-logo.jpg?raw=true 'SingularityNET')

# CNTK Finance Time Series Analysis

This service uses [CNTK Finance Timeseries](https://github.com/Microsoft/CNTK/blob/master/Tutorials/CNTK_104_Finance_Timeseries_Basic_with_Pandas_Numpy.ipynb) 
to predict whether or not, for an input date, market will be above or below the previous day.
[[Reference](https://cntk.ai/pythondocs/CNTK_301_Image_Recognition_with_Deep_Transfer_Learning.html)]


It is part of our third party [Time Series Analysis Services](https://github.com/singnet/time-series-analysis).

## Getting Started

### Requirements

- [Python 3.6.5](https://www.python.org/downloads/release/python-365/)
- [Node 8+ w/npm](https://nodejs.org/en/download/)

### Development

Clone this repository:

```
$ git clone https://github.com/singnet/time-series-analysis.git
$ cd finance/cntk-next-day-trend
```

### Running the service:

To get the `ORGANIZATION_NAME` and `SERVICE_NAME` you must have already published a service (check this [link](https://github.com/singnet/wiki/tree/master/tutorials/howToPublishService)).

Create the `SNET Daemon`'s config JSON file (`snetd.config.json`).

```
{
   "PRIVATE_KEY": "1000000000000000000000000000000000000000000000000000000000000000",
   "DAEMON_LISTENING_PORT": DAEMON_PORT,
   "DAEMON_END_POINT": "DAEMON_HOST:DAEMON_PORT",
   "ETHEREUM_JSON_RPC_ENDPOINT": "https://kovan.infura.io",
   "IPFS_END_POINT": "http://ipfs.singularitynet.io:80",
   "REGISTRY_ADDRESS_KEY": "0x2e4b2f2b72402b9b2d6a7851e37c856c329afe38",
   "PASSTHROUGH_ENABLED": true,
   "PASSTHROUGH_ENDPOINT": "SERVICE_GRPC_HOST:SERVICE_GRPC_PORT",  
   "ORGANIZATION_NAME": "ORGANIZATION_NAME",
   "SERVICE_NAME": "SERVICE_NAME",
   "LOG": {
       "LEVEL": "debug",
       "OUTPUT": {
            "TYPE": "stdout"
           }
   }
}
```

For example:

```
$ cat snetd.config.json
{
   "PRIVATE_KEY": "1000000000000000000000000000000000000000000000000000000000000000",
   "DAEMON_LISTENING_PORT": 7009,
   "DAEMON_END_POINT": "http://54.203.198.53:7009",
   "ETHEREUM_JSON_RPC_ENDPOINT": "https://kovan.infura.io",
   "IPFS_END_POINT": "http://ipfs.singularitynet.io:80",
   "REGISTRY_ADDRESS_KEY": "0x2e4b2f2b72402b9b2d6a7851e37c856c329afe38",
   "PASSTHROUGH_ENABLED": true,
   "PASSTHROUGH_ENDPOINT": "http://localhost:7003",
   "ORGANIZATION_NAME": "snet",
   "SERVICE_NAME": "cntk-next-day-trend",
   "LOG": {
       "LEVEL": "debug",
       "OUTPUT": {
           "TYPE": "stdout"
           }
   }
}
```
Install all dependencies:
```
$ pip3 install -r requirements.txt
```
Generate the gRPC codes:
```
$ sh buildproto.sh
```
Start the service and `SNET Daemon`:
```
$ python3 run_next_day_trend_service.py
```

### Calling the service:

Inputs:
  - `source`: Source to get market data (ie. yahoo, check this [link](https://github.com/pydata/pandas-datareader/blob/master/pandas_datareader/data.py#L306)).
  - `contract`: Label of asset (like "SPY").
  - `start_date`: Start date of training dataset.
  - `end_date`: End date of training dataset.
  - `target_date`: Date that will be analysed.
  - The date delta must be >= 100 days.

Local (testing purpose):

```
$ python3 test_stock_prediction_service.py 
Endpoint (localhost:7003): 
Method (trend): 
Source(yahoo): 
Contract(SPY): AMZN
Start Date(2000-01-01): 2017-01-01
End Date(2009-01-01): 2017-11-28
Target Date(2018-11-12): 2018-11-28
{'UP': 0.53}
```

Through SingularityNET (follow this [link](https://github.com/singnet/wiki/blob/master/tutorials/howToPublishService/README.md) 
to learn how to publish a service and open a payment channel to be able to call it):

Assuming that you have an open channel (`id: 0`) to this service:

```
$ snet client call 0 0.00000001 54.203.198.53:7009 trend '{"source": "yahoo", "contract": "APPL", "start_date": "2017-01-01", "end_date": "2017-10-31", "target_date": "2018-11-28"}'
...
Read call params from cmdline...

Calling service...

    response:
        {'DOWN': 0.48}
```

## Contributing and Reporting Issues

Please read our [guidelines](https://github.com/singnet/wiki/blob/master/guidelines/CONTRIBUTING.md#submitting-an-issue) before submitting an issue. 
If your issue is a bug, please use the bug template pre-populated [here][issue-template]. 
For feature requests and queries you can use [this template][feature-template].

## Authors

* **Artur Gontijo** - *Maintainer* - [SingularityNET](https://www.singularitynet.io)
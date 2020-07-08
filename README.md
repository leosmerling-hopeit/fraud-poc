# Fraud POC
> This is a prototype/poof-of-concept of a ML solution for Fraud Detection for e-commerce,


```python
#hide
```

[Dask](https://dask.org/) is a distributed processing engine for Python that can be used to process high data loads distributed environments, such a cluster. It has APIs built on top of popular Numpy and Pandas libraries.

[hopeit.engine](https://github.com/hopeit-git/hopeit.engine): is an open-source library that enables to quickly develop microservices in Python. hopeit.engine is built on top of aiohttp to provide http endpoints and async processing, and also provides distributed processing of streaming events using [Redis Streams](https://redis.io/topics/streams-intro).

The repo shows and end-to-end example of:
- Data preprocessing and partitioning (using Dasks Dataframes API)
- Feature calculation (using Dasks Dataframes API)
- Preparing data for model training (using Dasks Dataframes API)
- Training a model (distributed Dask XGBoost)
- Preparing data to serve predictions (using Dask + Redis)
- Prepare and run a microservice to orchestrate and monitor the data + training pipeline (using hopeit.engine)
- Prepare and run a microservice to predict fraud on new orders (using hopeit.engine) 

**DISCLAIMER**: The objective of this project is to show an example on how Data + Feature Extraction +
Model Trainig + Prediction can be developed and prepared for production. The data used for this example
is randomly generated orders, and neither the features selected and model parameteres were optimized
given the nature of data used.

To enable development, testing and working with the data in an unified environment I use [nbdev](https://github.com/fastai/nbdev). nbdev allows to explore data, create the services and test using Jupyter Notebooks. hopeit.engine and Dask plays well also with Juypyter notebooks, so the whole pipeline and prediction service can be developed and tested from Jupyter.

Let's get started:

* I recommend to install [Anaconda](https://docs.anaconda.com/anaconda/install/) (virtualenv can be used also -- not tested --)

* Create a conda environment, activate and install jupyterlab, nbdev and dask
```
conda create -n fraud-poc python=3.7
conda activate fraud-poc
conda install jupyterlab
conda install -c conda-forge dask graphviz python-graphviz 
pip install nbdev
nbdev_install_git_hooks
```

* Install hopeit.engine from provided library:
```
cd install
source install-hopeit-engine.sh
cd ..
```

* Finally install this project and dependencies in development mode
```
pip install -e .
```

* In order to run the microservices (optional) Redis is required. You can run redis for development, from the provided docker configuration:
```
cd docker
pip install docker-compose
docker-compose up -d redis
cd ..
```

* To open, visualize and edit notebooks run from the root folder of the project
```
jupyter lab
```



### Overview:

* Notebooks prefixed from 00* to 08* are created for each component/event of the pipeline and prediction service. Check each notebook for a brief description of what they do:
    
* Cells marked with #export, will generate a python file inside fraud_poc/ folder that can be executed by hopeit.engine
        
* To generate/update the code, run the cell containing "! nbdev_build_lib" (Code is already generated in the repo)
        
* Usually the last cells of the notebooks, are a test case that can be run locally and invoke the generated file, gather data and do some checks/analysis.        
        
* Inside config/ folder there are configuration files to run two microservices:

    * `training_pipeline.json` and `openapi-training.json` describe the service to run data preparation and training pipeline using hopeit.engine
    
    * `fraud-service.json` and `openapi-service.json` configure a service to perform real-time predictions on new orders based on the training model and aggregated data
    

### Data processing and training pipeline

* To run training pipeline service:

```
hopeit_server run --config-files=config/server.json,config/training-pipeline.json --api-file=config/openapi-training.json --start-streams --port=8020
```
        
You should see a couple endpoints in http://localhost:8020/api/docs

* The first endpoint "Data: Make Sample Data" will run the whole data+training pipeline end to end if you click in `Try It`
![](docs/img/api01.png)

1) **create-sample-data**: will create random orders in parquet format into folder `./data/raw/`. This dataset is partitioned by time periods, i.e. 1 file x month in this example. Once this step is finished the end of the job will be notified using hopeit.engine streams funcionallity and the next job will take place once the event is consumed.

2) **preprocess**: reads data generated in previous step and creates new output files partitioned by customer_id and email, so aggregations on those two dimensions can be perform more efficiently. Again, once the job is finished, the next step will be notified.

3) **feature-calc**: calculates aggregations on customer_ids and emails (i.e. accumulates most recent emails, ip_addrs, counts, order_amounts, etc) and stored a new data set of orders enriched with this extra information.

4) **training-data**: prepares data for training: obtaing lables for the order (in this POC is jus assigned using a combination of calculations with some randomness) and creates a more balanced dataset subsampling non-fraud cases, and creates a validation set using more recent non-fraud and fraud labeled transactions. Next step is notified when data is ready.

5) **train-model**: trains an XGBoost model on sampled data using Dask distributed implementation. Validates model precision and recall using validation dataset and if validation passes a configured threshold, model is copied to be used in prediction service.

6) **prepare-db**: stores most recent customer_id and email features calculated in step 3) into a Redis database that can be used for real-time prediction service. (Notice that this data should be continuosly updated on new orders but this is not provided in this example)

Since data generation could be tedious, there is a second endpoint that allows to run just form step 02, assuming
you already have raw data:
![](docs/img/api02.png)







### Fraud prediction service

To run the service prediction service:

```
hopeit_server run --config-files=config/server.json,config/fraud-service.json --api-file=config/openapi-service.json --start-streams --port=8021
```

You can try the endpoint providing order information using in http://localhost:8021/api/docs

* First extract some valid customer_id and email using:
```
curl -X GET "http://localhost:8021/api/fraud-poc/0x0x1-service/test/find-orders?prefix=*&num_items=10" \
 -H "Accept: application/json" 
```
This POC only can predict fraud for known customer_id and email in the generated data.

Using a customer_id and email, pass a new order to the service using the Live: Predict Endpoint:
![](docs/img/api03.png)

And check the results, all calcualted features plus an is_fraud field is returned:
```
```



I Hope you enjoyed it!

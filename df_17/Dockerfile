FROM python

RUN pip install sklearn scipy numpy https://github.com/tivvit/GDAX-Python/archive/master.zip docopt zmq elasticsearch ujson

ENTRYPOINT ["python", "/app/simulate.py"]
CMD [""]
'''
Sample parser for ExPath Client
'''
import base64
import datetime
import json
import threading

# import requests

from bson import ObjectId, json_util

from manager.client import Client
from manager.reader import ScanReader

# PACKAGES = requests.GET(
#     'https://hq.delhivery.com/api/p/info/23033712570/.json').json();
HANDLE = open('fixtures/packages.json', 'r')
PACKAGES = json.load(HANDLE)
HANDLE.close()


HANDLE = open('fixtures/vertices.json', 'r')
VERTICES = json.load(HANDLE)
HANDLE.close()

HANDLE = open('fixtures/edges.json', 'r')
EDGES = json.load(HANDLE)
HANDLE.close()

CLIENT = Client(host='Expath-Fletcher-ELB-544799728.us-east-1.elb.amazonaws.com', port=80)


class DTEncoder(json.JSONEncoder):
    '''
    Encode datetime object as ISO String
    '''

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, ObjectId):
            return json.dumps(obj, default=json_util.default)
        return super(DTEncoder, self).default(obj)


def push_to_stream(package, stream):
    '''
    Push package information off HQ to a stream which tests are going to
    execute. Stream simulates Kinesis behavior
    '''
    npack = {}

    for key, value in package.items():
        npack[key] = value

    npack['s'] = []

    for status in package['s']:
        npack['s'].append(status)
        npack['cs'] = status
        stream.append(base64.b64encode(json.dumps(npack, cls=DTEncoder)))


def test_handler(stream):
    '''
    Run tests on streamed data.
    Stream simulates Kinesis behavior
    '''
    fhandle = open('fixtures/data.json', 'w')
    records = []

    for data in stream:
        value = json.loads(base64.b64decode(data))
        reader = ScanReader(CLIENT, store=True)
        try:
            reader.read(value)
        except ValueError:
            continue
        records.extend(reader.data)
    CLIENT.close()
    fhandle.write(json.dumps(records))
    fhandle.close()


def run(load=False):
    '''
    Run actual tests
    '''
    if load:
        prepare()
    threads = []
    stream = []

    for package in [PACKAGES[0]]:
        thread = threading.Thread(
            target=push_to_stream, args=(package, stream))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    test_handler(stream)


def prepare():
    '''
    Dump vertex/edge data from fixtures to Fletcher
    '''
    CLIENT.add_vertices(VERTICES)
    CLIENT.add_edges(EDGES)

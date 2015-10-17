'''
This module defines the various classes used to represent records
for nodes, vertices and paths being used/populated by Expected Path
'''

from bson import ObjectId

from pymongo.cursor import CursorType

from .utils import recurse_get_attribute, recurse_set_attribute

from ..database.mongo import db_connection


class BaseModel(dict):
    '''
    The base model from which all other models are derived
    Contains accessors to read from/write to mongo db
    '''
    __collection__ = None
    __database__ = 'rebar'
    __auth__ = None

    __unique_keys__ = []

    @classmethod
    def get_connection(cls):
        '''
        Fetches a client to the database
        '''

        connect = db_connection(cls.__database__)

        if isinstance(cls.__auth__, tuple):
            connect.authenticate(cls.__auth__[0], cls.__auth__[1])

        if cls.__collection__:
            connect = connect[cls.__collection__]

        return connect

    @classmethod
    def find_one(cls, filter_dict):
        '''
        Returns a single instance matching the filter dict in the database
        '''

        if isinstance(filter_dict, (str, ObjectId)):
            if isinstance(filter_dict, str):
                filter_dict = {'_id': ObjectId(filter_dict)}
            else:
                filter_dict = {'_id': filter_dict}

        if not isinstance(filter_dict, dict):
            raise ValueError()

        connection = cls.get_connection()
        try:
            return cls(**connection.find_one(filter_dict))
        except TypeError:
            return None

    @classmethod
    def find(cls, filter_dict):
        '''
        Returns instances matching filter dict in the database
        '''

        if not isinstance(filter_dict, dict):
            raise ValueError()

        connection = cls.get_connection()
        results = connection.find(filter_dict, cursor_type=CursorType.EXHAUST)

        for result in results:
            yield cls(**result)

    @classmethod
    def count(cls, filter_dict):
        '''
        Returns the count of instances matching filter dict in the database
        '''

        if not isinstance(filter_dict, dict):
            raise ValueError()

        connection = cls.get_connection()
        return connection.find(filter_dict).count()

    @classmethod
    def all(cls):
        '''
        Returns all the instances for this model in the database
        '''
        return cls.find({})

    @classmethod
    def update(cls, filter_dict, update_dict, multi=True):

        if not isinstance(filter_dict, dict):
            raise ValueError()

        if not isinstance(update_dict, dict):
            raise ValueError()

        connection = cls.get_connection()
        connection.update(filter_dict, update_dict, multi=multi)

    def __setattr__(self, attribute, value):
        attributes = attribute.split('.')
        recurse_set_attribute(self, attributes, value)

    def __getattr__(self, attribute):
        attributes = attribute.split('.')
        return recurse_get_attribute(self, attributes)

    def save(self):
        '''
        Save the instance to the database ( or update it if it exists )
        '''
        connection = self.get_connection()

        if '_id' in self:
            connection.update_one(
                {'_id': self['_id']},
                {'$set': self}, upsert=True
            )
        else:
            result = connection.insert_one(self)
            self['_id'] = result.inserted_id

    def insert_one(self):
        '''
        Insert a singlular record into the database
        '''
        connection = self.get_connection()

        if ['_id'] in self:
            raise ValueError('Only records lacking _id can be inserted')
        result = connection.insert_one(self)
        self['_id'] = result.inserted_id

    def remove(self):
        '''
        Delete self from records
        '''
        connection = self.get_connection()
        connection.delete_one({'_id': self['_id']})


class DeliveryCenter(BaseModel):
    '''
    Represents a vertex in a graph
    '''
    __collection__ = 'nodes'
    __unique_keys__ = [('code', )]

    # structure = {
    #     'code': GenericField(type=str),
    #     'name': GenericField(type=str, required=False),
    #     'active': GenericField(type=bool)
    # }


class Connection(BaseModel):
    '''
    Represents available edges for a graph
    '''

    __collection__ = 'edges'
    __unique_keys__ = [('index', )]

    # structure = {
    #     'name': GenericField(type=str),
    #     'origin': ForeignKey(type=DeliveryCenter),
    #     'destination': ForeignKey(type=DeliveryCenter),
    #     'departure': TimeField(),
    #     'duration': GenericField(type=int),
    #     'active': GenericField(type=bool),
    #     'mode': ChoiceField(type=str, choices=[
    #         'Local', 'Surface', 'Railroad', 'Air'
    #     ]),
    #     'index': GenericField(type=int),
    # }


class ScanRecord(BaseModel):
    '''
    This model records various scans parsed to maintain uniqueness
    of parsed scans
    '''

    __collection__ = 'scans'
    __unique_keys__ = [('wbn', 'ist', 'act'), ]

    # structure = {
    #     'wbn': GenericField(type=str),
    #     'pid': GenericField(type=str),
    #     'act': GenericField(type=str),
    # }


class WaybillLocker(BaseModel):
    '''
    Allows a parser to lock a particular waybill
    '''
    __collection__ = 'wbn_locks'
    __unique_keys__ = ['wbn']

    # structure = {
    #     'wbn': GenericField(type=str),
    # }


class GraphNode(BaseModel):
    '''
    Represents a sub-path in the graph of EP
    Each sub-path is defined by the vertex, edge, parent and parent edge
    '''
    __collection__ = 'paths'
    __unique_keys__ = []

    # structure = {
    #     'wbn': GenericField(type=str),
    #     'pd': DateTimeField(required=False),
    #     'vertex': ForeignKey(type=DeliveryCenter, required=False),
    #     'edge': ForeignKey(type=Connection, required=False),
    #     'parent': ForeignOidKey(
    #         type='rebar.models.base.GraphNode', required=False),
    #     'p_con': ForeignKey(type=Connection, required=False),
    #     'e_arr': DateTimeField(required=False),
    #     'e_dep': DateTimeField(required=False),
    #     'a_arr': DateTimeField(required=False),
    #     'a_dep': DateTimeField(required=False),
    #     'dst': GenericField(type=bool),
    #     'st': ChoiceField(type=str, choices=[
    #         'reached', 'active', 'failed', 'future', 'inactive'
    #     ]),  # Statuses
    #     'f_at': ChoiceField(type=str, choices=[
    #         'center', 'cin', 'cout'
    #     ]),  # Failure At: Center, Connection In/Out
    #     'stc': ChoiceField(type=str, choices=[
    #         'regen', 'dmod', 'hard', 'soft', 'mroute'
    #     ]),  # Status Cause: Regen, Destination Mod, Hard/Soft Fail
    #     'cr_at': DateTimeField(auto_add_now=True, required=True),
    # }

    @classmethod
    def find_by_parent(cls, parent):
        '''
        Allows lookup of a node given the parent node
        '''
        return cls.find_one({'parent._id': parent['_id'], 'st': 'future'})

    @property
    def reference(self):
        '''
        Returns self as oid reference
        '''
        return {'_id': self['_id']}

    def deactivate(self, stc=None, f_at=None):
        '''
        Deactivates a node in the graph i.e. st = 'failed'
        Also marks all children elements as inactive i.e. st = 'inactive'
        '''
        self['st'] = 'failed'

        if stc:
            self['stc'] = stc

        if f_at:
            self['f_at'] = f_at

        self.save()
        self.update(
            {'_id': {'$gt': self['_id']}, 'wbn': self['wbn'], 'st': 'future'},
            {'$set': {'st': 'inactive', 'dst': False}}
        )

    def reached(self, stc=None, f_at=None):
        '''
        Marks a node as reached in the graph i.e. st = 'Reached'
        '''
        self['st'] = 'reached'

        if stc:
            self['stc'] = stc

        if f_at:
            self['f_at'] = f_at
        self.save()

    def activate(self):
        '''
        Activates a node in the path i.e. st = 'Active'
        '''
        self['st'] = 'active'
        self.save()

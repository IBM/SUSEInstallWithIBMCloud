from aenum import Enum
import json
from json import JSONEncoder

class BaseEnum(Enum):
    def __str__(self):
        return self.value
    def __repr__(self):
        return self.value
    @classmethod
    def getType(cls,value):
        for _, member in cls.__members__.items():
            if member.value == value:
                return member
        raise Exception("Unknown enum for class %s: %s" % (cls.__name__, value) )
    @classmethod
    def getTypes(cls):
        """
        Returns a list of strings with the values of the enums
        
         @rtype list: list with the possible values
        """ 
        result = []
        for _, member in cls.__members__.items():
            result.append(member.value)
        return result

class BaseObject:
    """BaseObject"""
    def __repr__(self):
        """To string representation"""
        return "%s %s" % (self.__class__.__name__,self.__dict__)

    @classmethod
    def _copyProps(cls,mapping, target, source=None, sourceDict=None):
        """
            Copies properties from "source" and populate into "target".
            The mapping is an array of arrays. The inner arrays 
            are the property mappings:
            [
                [<sourceProp>, <targetProp>]
                [<prop>]
            ]

            First form is used to load a source prop into a differently named target prop:
                target.__dict__[<targetProp>] = source.__dict__[sourceProp] or sourceDict[sourceProp]
            The second form is used to load a source prop into the same named target prop:
                 target.__dict__[<prop>] = source.__dict__[prop] or sourceDict[prop]
        """
        if mapping:
            objDict = target.__dict__
            if source or sourceDict:
                data = sourceDict if sourceDict else source.__dict__
                for prop in mapping:
                    if len(prop) != 1 or len(prop) != 2:
                        sourceProp = prop[0]
                        targetProp = prop[1] if len(prop) > 1 else prop[0]
                        objDict[targetProp] = data[sourceProp] if sourceProp in data else None
            else:
                raise Exception("Neither source nor sourceDict specified.")

class JsonSerializable:
    def jsonDict(self):
        outDict = self.__dict__.copy()
        for k,v in outDict.items():
            if isinstance(v,BaseEnum):
                outDict[k] = v.value

        return outDict
    def toJson(self):
        return json.dumps(self.jsonDict())

class JsonUtil:
    class JsonEncoder(JSONEncoder):
        def default(self, o):
            if isinstance(o, JsonSerializable):
                return o.jsonDict()
            return json.JSONEncoder.default(self, o)
    @classmethod
    def dumps(cls, obj, skipkeys=False, ensure_ascii=True, check_circular=True, allow_nan=True, indent=None, separators=None, encoding='utf-8', default=None, sort_keys=False, **kw):
        return json.dumps(obj, cls=cls.JsonEncoder, skipkeys=skipkeys, ensure_ascii=ensure_ascii, check_circular=check_circular, allow_nan=allow_nan, indent=indent, separators=separators, encoding=encoding, default=default, sort_keys=sort_keys, *kw)

"""Reject malformed payloads before SQL or domain logic; never echo supplied values."""
import math

TEXT_FIELDS = {'username','password','current_password','new_password','code','name','description',
 'station','asset_tag','serial','status','reason','notes','early_explanation','comment','decision',
 'operation_key','sku','bin','supplier','supplier_number','delivery_reference','order_reference',
 'report','search','event','from_date','to_date','direction','role'}

def payload(value, depth=0):
    if depth>8: raise ValueError('Payload nesting limit.')
    if isinstance(value,dict):
        if len(value)>100: raise ValueError('Too many fields.')
        for key,item in value.items():
            if not isinstance(key,str) or len(key)>80: raise ValueError('Invalid field.')
            if key in TEXT_FIELDS and not isinstance(item,str): raise ValueError('Expected text.')
            payload(item,depth+1)
    elif isinstance(value,list):
        if len(value)>1000: raise ValueError('Too many items.')
        for item in value: payload(item,depth+1)
    elif isinstance(value,str):
        if len(value)>4000 or '\x00' in value: raise ValueError('Invalid text.')
    elif type(value)==int:
        if abs(value)>2147483647: raise ValueError('Integer out of range.')
    elif type(value)==float:
        if not math.isfinite(value): raise ValueError('Invalid number.')
    elif value is not None and not isinstance(value,bool): raise ValueError('Invalid value.')

def object_pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError('Duplicate JSON key.')
        result[key]=value
    return result

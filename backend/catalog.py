"""Catalog validation; inventory balances are never metadata fields."""
from decimal import Decimal, InvalidOperation

class CatalogError(ValueError): pass

def text(data,key,optional=False):
    value=data.get(key,'') if optional else data.get(key)
    if not isinstance(value,str): raise CatalogError(f'{key} must be text.')
    value=value.strip()
    if not optional and not value: raise CatalogError(f'{key} is required.')
    if len(value)>240: raise CatalogError(f'{key} must be 240 characters or fewer.')
    return value

def integer(data,key,minimum=0):
    value=data.get(key)
    if type(value)!=int or value<minimum: raise CatalogError(f'{key} must be an integer of at least {minimum}.')
    return value

def part_details(db,data):
    sku=text(data,'sku').upper()
    try:
        if type(data.get('cost')) not in (int,float): raise CatalogError('cost must be a number.')
        cost=Decimal(str(data['cost']))
        if not cost.is_finite() or cost<0 or cost>=Decimal('1000000000'): raise CatalogError('cost must be a nonnegative finite number below 1 billion.')
        if cost!=cost.quantize(Decimal('0.01')): raise CatalogError('Unit cost supports at most two decimal places.')
    except InvalidOperation as e: raise CatalogError('Invalid unit cost.') from e
    types=data.get('type_ids')
    if not isinstance(types,list) or not types or any(type(t)!=int or t<1 for t in types): raise CatalogError('Select at least one compatible machine type.')
    for t in set(types):
        if not db.execute('SELECT 1 FROM types WHERE id=?',(t,)).fetchone(): raise CatalogError('A selected machine type no longer exists.')
    threshold=integer(data,'threshold'); target=integer(data,'target')
    if target<threshold: raise CatalogError('Target stock must be at least the reorder threshold.')
    return {'sku':sku,'name':text(data,'name'),'bin':text(data,'bin'),
            'supplier':text(data,'supplier',True),'supplier_number':text(data,'supplier_number',True),
            'cost':float(cost),'threshold':threshold,'target':target,
            'lead_days':integer(data,'lead_days'),'interval_days':integer(data,'interval_days',1),
            'type_ids':sorted(set(types))}

def unique_sku(db,sku,exclude=None):
    for p in db.execute('SELECT id,sku FROM parts'):
        if p['id']!=exclude and p['sku'].strip().casefold()==sku.casefold():
            raise CatalogError('SKU already exists. Choose a unique SKU.')

def unique_type_name(db,name,exclude=None):
    for t in db.execute('SELECT id,name FROM types'):
        if t['id']!=exclude and t['name'].strip().casefold()==name.casefold():
            raise CatalogError('Machine type name already exists. Choose a unique name.')

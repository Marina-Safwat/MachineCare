"""Equipment scopes: whole-building grants OR individual line grants.
A line grant follows the stable line ID and never grants access to sibling lines.
"""

def grants(db, user_id):
    return ({r[0] for r in db.execute('SELECT building_id FROM access WHERE user_id=?',(user_id,))},
            {r[0] for r in db.execute('SELECT line_id FROM line_access WHERE user_id=?',(user_id,))})

def allows(scope, building_id, line_id):
    buildings, lines=scope
    return building_id in buildings or line_id in lines

def covers(db, supervisor, technician):
    """Whole-building technicians require a whole-building lead grant, including future lines."""
    lead_buildings, lead_lines=supervisor
    tech_buildings, tech_lines=technician
    if not tech_buildings<=lead_buildings: return False
    for line_id in tech_lines:
        line=db.execute('SELECT building_id FROM lines WHERE id=?',(line_id,)).fetchone()
        if not line or not allows((lead_buildings,lead_lines),line['building_id'],line_id): return False
    return True

def validate(db, building_ids, line_ids):
    for key, values, table in [('building_ids',building_ids,'buildings'),('line_ids',line_ids,'lines')]:
        if not isinstance(values,list) or any(type(v)!=int or v<1 for v in values):
            raise ValueError(f'{key} must be a list of positive integer IDs.')
        for value in set(values):
            if not db.execute(f'SELECT 1 FROM {table} WHERE id=?',(value,)).fetchone():
                raise ValueError(f'Selected {"building" if table=="buildings" else "line"} does not exist.')
    return set(building_ids), set(line_ids)

def write(db,user_id,scope):
    buildings,lines=scope
    db.execute('DELETE FROM access WHERE user_id=?',(user_id,))
    db.execute('DELETE FROM line_access WHERE user_id=?',(user_id,))
    for b in sorted(buildings): db.execute('INSERT INTO access VALUES(?,?)',(user_id,b))
    for line in sorted(lines): db.execute('INSERT INTO line_access VALUES(?,?)',(user_id,line))

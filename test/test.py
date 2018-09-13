import sotoddb

print('Creating the database')
db = sotoddb.get_example('DetDB')

print('Test 1: how many dets have array_code=HF1?')
X = db.get_dets(props={'base.array_code': 'HF1'})
print('  Answer: %i' % len(X))
print('  The first few are:')
for x in X[:5]:
    print('    ' + str(x))
print()

print('Test 2: Get (array, wafer) for a bunch of dets.')
u2 = db.get_props(X, props=['base.array_code', 'wafer_code'])
pairs = [str(x) for x in set(u2)]
print('  Distinct pairs:')
for p in pairs:
    print('    ' + str(p))
print()

print('Test 3: Make a copy of just the LF1 dets.')
db2 = db.copy()
X = db2.get_dets(props={'array_code': 'LF1'})
db2.reduce(X, time0=-1, time1=1)
db3 = db2.copy(map_file='test_LF1.sqlite', clobber=True)
print()


print('Loading from disk...')
db1 = sotoddb.DetDB.from_file('test_out.sqlite')
print('Detector count: %i' % len(db1.get_dets()))
print()

#print('Test docs...')
#print(help(db1.create_table))
    

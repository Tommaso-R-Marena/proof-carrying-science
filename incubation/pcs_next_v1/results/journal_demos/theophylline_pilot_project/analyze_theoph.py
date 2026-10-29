# Non-executing discovery target for journal demo
import csv
rows=list(csv.DictReader(open('Theoph.csv')))
assert len(rows)==132

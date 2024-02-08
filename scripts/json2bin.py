# Converts a results file from the old JSON format to the new (2024-02) binary format.
import json
import os

from utils import results_file
from utils.timing import TimeIt

json_filename = './results/results.json'

with TimeIt('Loading JSON result'):
    json_results = json.loads(open(json_filename, 'r').read())

bin_filename = json_filename+'.bin'
if os.path.exists(bin_filename):
    os.remove(bin_filename)

with TimeIt('Writing binary file'):
    for result in json_results:
        results_file.append(bin_filename, result)

# Now test the result.
with TimeIt('Reading binary file'):
    bin_results = results_file.load(bin_filename)

assert bin_results == list(reversed(json_results))


# Results on Raspberry Pi, with a ~70MB JSON file:
# Loading JSON result...done in 2.377 seconds.
# Writing binary file...done in 2.918 seconds.
# Reading binary file...done in 3.142 seconds.
# Binary file is not worth it.

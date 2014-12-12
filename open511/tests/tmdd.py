import json
import os
from unittest import TestCase

from open511.utils.input import load_path

class TMDDConversionTestCase(TestCase):
	maxDiff = None

	def _compare(self, input_filename, output_filename):
		input_filename = os.path.join(os.path.dirname(__file__), 'fixtures', input_filename)
		output_filename = os.path.join(os.path.dirname(__file__), 'fixtures', output_filename)
		converted, _ = load_path(input_filename)
		converted = json.loads(json.dumps(converted)) # Run it through JSON to normalize

		with open(output_filename) as f:
			correct_json = json.load(f)
		self.assertEqual(converted, correct_json)

	def test_example_1(self):
		self._compare('tmdd-input-1.xml', 'tmdd-output-1.json')

	def test_example_2(self):
		self._compare('tmdd-input-2.xml', 'tmdd-output-2.json')

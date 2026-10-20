"""Offline same-library union and truthful reading-state checks."""
import json
from pathlib import Path
import tempfile
import unittest
from merge_ima_snapshots import merge

class MergeTests(unittest.TestCase):
    def test_union_keeps_discovery_paths_without_claiming_read_or_complete(self):
        with tempfile.TemporaryDirectory() as td:
            paths = [Path(td)/'a.json', Path(td)/'b.json']
            a = {'media_id': 'a', 'title': 'synthetic.pdf', 'media_type': 1, 'discovered_via': ['list:root']}
            b = {**a, 'discovered_via': ['search:test']}
            folder = {'media_id': 'folder', 'title': 'Synthetic folder', 'media_type': 99}
            for p, items in zip(paths, [[a, folder], [b, {'media_id': 'b', 'title': 'synthetic.docx', 'media_type': 3}]]):
                p.write_text(json.dumps({'knowledge_base_id': 'synthetic-kb', 'items': items}), encoding='utf-8')
            snapshot, queue = merge(paths)
            self.assertEqual(len(snapshot['items']), 3)
            self.assertEqual(len(queue), 2)
            self.assertEqual(snapshot['items'][0]['discovered_via'], ['list:root', 'search:test'])
            self.assertEqual(snapshot['status'], 'MERGED_SCOPE_UNKNOWN')
            self.assertTrue(all(x['read_status'] == 'METADATA_ONLY' and x['decision'] is None for x in queue))

    def test_different_library_snapshots_cannot_be_merged(self):
        with tempfile.TemporaryDirectory() as td:
            paths = [Path(td)/'a.json', Path(td)/'b.json']
            for i, p in enumerate(paths):
                p.write_text(json.dumps({'knowledge_base_id': str(i), 'items': []}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'different knowledge bases'):
                merge(paths)

if __name__ == '__main__':
    unittest.main(verbosity=2)

"""A-077 replacement is independent of adventurers and base construction."""
import unittest

from test_card_audit_fixes import game, select


class FireworksEffect(unittest.TestCase):
    def prepare(self, available=0, base=False, solo=False):
        e, p = game(solo=solo)
        p.update(hand=[32], gold=100, tags=['scrap', 'scrap'], available=available)
        territory = next(c for c in e.state['board'] if not e._tile_locked(c) and not c.get('boss'))
        territory.update(owner=0, base=base)
        target = next(c for c in e._neighbors(territory)
                      if c['owner'] is None and not c.get('boss') and not e._tile_locked(c))
        target.update(loot='tile1', revealed=True)
        e.apply(0, dict(type='play', card=32))
        self.assertEqual(e.state['pending']['task']['step']['op'], 'branch')
        return e, territory['id'], target['id']

    def replace(self, e, target):
        select(e, [0])
        pending = e.state['pending']
        self.assertIsNotNone(pending, 'Replacement must remain available without adventurers or a base')
        self.assertEqual(pending['task']['step']['op'], 'replace')
        eligible = {c['id'] for c in e.state['board'] if c['owner'] is None
                    and not c.get('boss') and not e._tile_locked(c)
                    and any(n['owner'] == 0 for n in e._neighbors(c))}
        self.assertEqual({o['value'] for o in pending['options']}, eligible)
        select(e, [next(i for i, o in enumerate(pending['options']) if o['value'] == target)])
        self.assertEqual(e._cell(target)['loot'], 'tile21')
        self.assertTrue(e._cell(target)['revealed'])
        self.assertIsNone(e._cell(target)['owner'])

    def test_replace_without_adventurers_or_base(self):
        for solo in (False, True):
            for base in (False, True):
                with self.subTest(solo=solo, base=base):
                    e, territory, target = self.prepare(base=base, solo=solo)
                    self.replace(e, target)
                    self.assertEqual(e._player(0)['available'], 0)
                    self.assertEqual(e._cell(territory)['base'], base)
                    self.assertIsNone(e.state['pending'])
                    self.assertFalse(e.state['effects'])
                    self.assertEqual(e.state['action_count'], 1)
                    self.assertFalse(e.can_explore(0, target))

    def test_replace_then_optional_exploration(self):
        for skip in (False, True):
            with self.subTest(skip=skip):
                e, _, target = self.prepare(available=1)
                self.replace(e, target)
                pending = e.state['pending']
                self.assertEqual(pending['task']['step']['op'], 'explore')
                self.assertTrue(pending['optional'])
                if skip:
                    select(e, skip=True)
                else:
                    select(e, [next(i for i, o in enumerate(pending['options']) if o['value'] == target)])
                    self.assertEqual(e.state['pending']['task']['step']['op'], 'explore_payment')
                    select(e)
                self.assertEqual(e._player(0)['available'], 1 if skip else 0)
                self.assertEqual(e._cell(target)['owner'], None if skip else 0)
                self.assertIsNone(e.state['pending'])
                self.assertEqual(e.state['action_count'], 1)

    def test_gold_branch_without_adventurers(self):
        e, _, _ = self.prepare()
        before = e._player(0)['gold']
        select(e, [1])
        self.assertEqual(e._player(0)['gold'], before + len(e._player(0)['played']))
        self.assertEqual(e._player(0)['available'], 0)
        self.assertIsNone(e.state['pending'])


if __name__ == '__main__':
    unittest.main()

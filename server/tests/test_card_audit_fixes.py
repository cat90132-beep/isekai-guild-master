"""Printed-card regression cases through the shared authoritative engine."""
import unittest
from copy import deepcopy
from guild_engine import Engine
from guild_content import CARDS, CARD_GALLERY, HEROES, TILES, ACHIEVEMENTS, card_summary, requirement_summary


def game(hero='bai_white',solo=False,starter=0):
    e=Engine([dict(id=i,name=str(i),hero=hero if i==0 else 'bai_white')
              for i in range(1 if solo else 2)],seed=22,
             options=dict(solo=solo,setup_draft=False,start_player=starter))
    for p in e.state['players']:
        e.apply(p['id'],dict(type='research',cards=[]))
    return e,e._player(0)


def select(e,indices=None,skip=False,**payment):
    q=e.state['pending']
    e.apply(q['player'],dict(type='choice',choice_id=q['id'],
                           selected=indices or [],skip=skip,action=payment))


class PrintedCardFixes(unittest.TestCase):
    def test_event_gallery_and_text_follow_runtime_definitions(self):
        for number, card in CARDS.items():
            if number not in CARD_GALLERY:
                continue
            gallery = CARD_GALLERY[number]
            for field in ('name', 'price', 'requirements', 'costs', 'steps',
                          'action', 'available', 'draw', 'pot', 'gold_pro'):
                self.assertEqual(gallery.get(field), card.get(field), (number, field))
            self.assertEqual(card_summary(number), card_summary(card), number)
            self.assertEqual(requirement_summary(number), requirement_summary(card), number)
        self.assertIn('费用15金币', card_summary(221))
        self.assertIn('抽牌+1', card_summary(221))
        self.assertIn('药水+1', card_summary(78))
        self.assertNotIn('支付，', card_summary(61))

    def test_alchemy_investment_needs_no_life_tag(self):
        for solo in (False,True):
            e,p=game(solo=solo)
            p.update(hand=[221],gold=15,tags=[],tiles=[],played=[])
            before_pot,before_production=p['pot'],p['pot_pro']
            self.assertEqual(e._tags(p)['civ'],0)
            e.apply(0,dict(type='play',card=221))
            p=e._player(0)
            self.assertEqual(p['played'],[221])
            self.assertEqual(p['gold'],0)
            self.assertEqual((p['pot']-before_pot,p['pot_pro']-before_production),(1,1))
            self.assertEqual(len(p['hand']),1)
            self.assertEqual(e.score_breakdown(0)['cards'],1)
            self.assertIsNone(e.state['pending'])

    def test_siren_initial_discount_does_not_replay_clicked_card(self):
        for solo in (False,True):
            for copies in (1,2):
                e,p=game('siren_white',solo=solo)
                p.update(hand=[20]*copies,gold=100)
                e.apply(0,dict(type='play',card=20))
                select(e,[0]);select(e)
                p=e._player(0)
                self.assertEqual(p['played'],[20])
                self.assertEqual(p['hand'],[20]*(copies-1))
                self.assertEqual(p['gold'],100-max(0,CARDS[20]['price']-20))
                self.assertEqual((e.state['turn'],e.state['action_count']),(0,0))
                self.assertIsNone(e.state['pending'])

    def test_siren_initial_choice_does_not_auto_spend_normal_action(self):
        e,p=game('siren_white');p.update(hand=[20,9],gold=100)
        e.apply(0,dict(type='play',card=20))
        select(e,[1]);select(e)
        self.assertEqual(e._player(0)['played'],[9])
        self.assertEqual(e._player(0)['hand'],[20])
        self.assertEqual(e.state['action_count'],0)
        e.apply(0,dict(type='play',card=20))
        self.assertEqual(e._player(0)['played'],[9,20])
        self.assertEqual(e.state['action_count'],1)

    def test_siren_initial_discount_can_be_skipped(self):
        e,p=game('siren_white');p.update(hand=[20],gold=100)
        e.apply(0,dict(type='play',card=20));select(e,skip=True)
        self.assertEqual(e._player(0)['hand'],[20])
        self.assertEqual(e.state['action_count'],0)
        e.apply(0,dict(type='play',card=20))
        self.assertEqual(e._player(0)['gold'],100-CARDS[20]['price'])

    def test_baby_beast_attaches_one_or_two_and_rewards_each(self):
        for solo in (False,True):
            for count in (1,2):
                e,p=game(solo=solo);p.update(played=[200],tiles=['tile1','tile1'],strength=0)
                e.apply(0,dict(type='card_action',card=200))
                q=e.view(0)['pending']
                self.assertEqual((q['min'],q['max']),(1,2))
                select(e,list(range(count)))
                p=e._player(0)
                self.assertEqual((p['strength'],len(p['tiles'])),(count,2-count))
                self.assertEqual(len(e._card_states(p)[0]['tiles']),count)
                self.assertEqual(e._stat(p,'pieces'),2)
                self.assertEqual(e.score_breakdown(0)['cards'],1+count)

    def test_baby_beast_one_available_tile_and_invalid_counts(self):
        e,p=game();p.update(played=[200],tiles=['tile1'],strength=0)
        e.apply(0,dict(type='card_action',card=200))
        self.assertEqual(e.view(0)['pending']['max'],1)
        with self.assertRaises(ValueError):select(e,[])
        with self.assertRaises(ValueError):select(e,[0,1])
        select(e,[0]);self.assertEqual(e._player(0)['strength'],1)

    def test_truck_payment_optional_in_both_modes(self):
        for solo in (False,True):
            for pay in (False,True):
                e,p=game(solo=solo);p.update(hand=[1],tiles=['tile1'],gold=100)
                e.apply(0,dict(type='play',card=1))
                self.assertEqual(len(e._player(0)['hand']),1)
                self.assertTrue(e.state['pending']['optional'])
                select(e,[0] if pay else [],skip=not pay)
                self.assertEqual(len(e._player(0)['hand']),3 if pay else 1)
                self.assertEqual(len(e._player(0)['tiles']),0 if pay else 1)

    def test_gate_draws_only_after_optional_steps(self):
        e,p=game();p.update(tiles=['tile1','tile1'],hand=[35],gold=100)
        cell=next(c for c in e.state['board'] if not c.get('boss') and not c.get('blocked'))
        cell.update(loot='tile14',revealed=True,owner=None)
        e.apply(0,dict(type='play',card=35))
        self.assertEqual(len(e._player(0)['hand']),0)
        self.assertEqual(e.state['pending']['task']['step']['op'],'purify')
        select(e,skip=True)
        self.assertEqual(len(e._player(0)['hand']),0)
        select(e,skip=True)
        self.assertEqual(len(e._player(0)['hand']),1)

    def test_crystal_tomb_pay_three_strength(self):
        e,p=game();p.update(played=[57],strength=3,gold=0)
        e.apply(0,dict(type='card_action',card=57))
        select(e,[2])
        self.assertEqual((e._player(0)['strength'],e._player(0)['gold']),(0,15))

    def test_crystal_tomb_skipped_purify_grants_tile(self):
        e,p=game();p['tiles']=[]
        e._effects(p,dict(steps=CARDS[57]['steps']));e._drain_effects()
        if e.state['pending']:select(e,skip=True)
        self.assertEqual(e._player(0)['tiles'],['tile21'])

    def test_healer_may_flip_no_cards(self):
        e,p=game();p['played']=[94]
        e._effects(p,dict(steps=CARDS[94]['steps']));e._drain_effects()
        select(e,skip=True)
        self.assertFalse(e._card_states(e._player(0))[0]['face_down'])

    def test_furry_park_only_solo_capped(self):
        for solo,expected in ((True,40),(False,80)):
            e,p=game(solo=solo);p.update(gold=0,gold_pro=100)
            e._effects(p,dict(scaled=CARDS[96]['scaled']))
            self.assertEqual(e._player(0)['gold'],expected)

    def test_dual_tag_event_counts_once_and_loot_not_counted(self):
        e,p=game();p['played']=[193]
        e._gain_tags(p,['civ','character'],origin='card');e._drain_effects()
        self.assertEqual(e._card_states(e._player(0))[0]['counters'],1)
        e._gain_tags(p,['civ'],origin='tile');e._drain_effects()
        self.assertEqual(e._card_states(e._player(0))[0]['counters'],1)
        e._gain_tags(p,['character'],origin='card');e._drain_effects()
        self.assertEqual(e._card_states(e._player(0))[0]['counters'],2)

    def test_solo_all_effect_is_ignored_by_rulebook(self):
        for solo,expected in ((True,0),(False,1)):
            e,p=game(solo=solo);before=p['strength']
            e._effects(p,dict(steps=[dict(op='all',effect=dict(strength=1))]));e._drain_effects()
            self.assertEqual(e._player(0)['strength']-before,expected)

    def test_solo_achievement_requires_held_tiles(self):
        e,p=game(solo=True);p['tiles']=['tile1']*5
        self.assertEqual(e._stat(p,'controlled'),0)
        self.assertTrue(e._requirements(p,ACHIEVEMENTS['solo_normal_3']['requirements']))
        p['tiles']=[]
        for c in e.state['board'][:5]:c['owner']=0
        self.assertFalse(e._requirements(p,ACHIEVEMENTS['solo_normal_3']['requirements']))

    def test_quest_accepts_two_star_tile(self):
        e,p=game();p['tiles']=[next(k for k,t in TILES.items() if t.get('star')==2)]
        self.assertTrue(e._quest_met(p,24))

    def test_vee_flips_face_up_cards_and_rewards_each(self):
        e,p=game('vee_black');p['played']=[2,9,14]
        e._card_states(p)[2]['face_down']=True
        strength=p['strength']
        e._effects(p,HEROES['vee_black']['upgrade3']);e._drain_effects()
        self.assertEqual(len(e.state['pending']['options']),2)
        select(e,[0,1])
        self.assertTrue(all(m['face_down'] for m in e._card_states(e._player(0))))
        self.assertEqual(e._player(0)['strength']-strength,2)

    def test_macaron_payment_counts_stars(self):
        e,p=game('macaron_black');p['tiles']=[next(k for k,t in TILES.items() if t.get('star')==n) for n in (1,2)]
        gold=p['gold'];hand=len(p['hand'])
        e._effects(p,HEROES['macaron_black']['upgrade3']);e._drain_effects()
        select(e,[0,1])
        self.assertEqual(e._player(0)['gold']-gold,15)
        self.assertEqual(len(e._player(0)['hand'])-hand,1)

    def test_horn_counts_existing_face_up_extra_cost_events(self):
        e,p=game('horn_black');p['played']=[60,117,201,9]
        e._card_states(p)[2]['face_down']=True
        before=p['gold'];e._effects(p,HEROES['horn_black']['upgrade3'])
        self.assertEqual(e._player(0)['gold']-before,10)
        self.assertIsNone(e.state['pending'])

    def test_ayaka_normal_play_needs_no_wisdom(self):
        e,p=game('ayaka_revised');p.update(wisdom=0,hand=[9],gold=100)
        e.apply(0,dict(type='ability'));select(e,[0]);select(e,[0]);select(e)
        self.assertIn(9,e._player(0)['played'])

    def test_ayaka_select_achievement_is_private(self):
        e,p=game('ayaka_revised');before=len(p['achievements']);deck=len(e.state['achievement_deck'])
        e._effects(p,HEROES['ayaka_revised']['upgrade3']);e._drain_effects()
        self.assertEqual(len(e.state['pending']['options']),2)
        self.assertNotIn('options',e.view(1)['pending'])
        select(e,[1])
        self.assertEqual(len(e._player(0)['achievements']),before+1)
        self.assertEqual(len(e.state['achievement_deck']),deck-1)

    def test_alicia_first_action_reveals_two_then_resumes(self):
        e,p=game('alicia_red');p.update(hand=[9],gold=100)
        e.apply(0,dict(type='play',card=9))
        self.assertEqual(e.state['pending']['task']['step']['op'],'reveal')
        select(e,[0]);select(e,[0])
        self.assertIn(9,e._player(0)['played']);self.assertEqual(e.state['turn'],1)

    def test_elu_precedes_starter_and_has_normal_turn(self):
        e,p=game('elu_red_b',starter=1)
        self.assertEqual(e.state['turn'],0)
        p.update(hand=[9],gold=100)
        e.apply(0,dict(type='play',card=9))
        self.assertEqual(e.state['turn'],1)
        e.apply(1,dict(type='pass'))
        self.assertEqual(e.state['turn'],0)
        e,p=game('elu_red_b',solo=True)
        self.assertFalse(e.state.get('season_pre_actions'))

    def test_elu_can_discard_more_than_five(self):
        e,p=game('elu_red_b');p['hand']=[9]*7;before=p['gold']
        e._effects(p,HEROES['elu_red_b']['upgrade3']);e._drain_effects()
        select(e,list(range(7)))
        self.assertEqual(e._player(0)['gold']-before,21);self.assertEqual(e._player(0)['extra_actions'],1)

    def test_misha_solo_final_bonus_once_after_round_six(self):
        e,p=game('misha_red',solo=True);p['hero_level']=3;e.state['round']=6
        before=p['gold'];e.apply(0,dict(type='pass'))
        self.assertEqual(e._player(0)['gold']-before,20)
        self.assertEqual(e.state['phase'],'action')
        e.apply(0,dict(type='pass'))
        self.assertEqual(e.state['phase'],'finished')
        self.assertEqual(e._player(0)['gold']-before,20)

    def test_misha_multiplayer_bonus_at_end_of_final(self):
        e,p=game('misha_red');p['hero_level']=3
        e.state.update(phase='final',final_remaining=[1,0],turn=0)
        before=p['gold'];e.apply(0,dict(type='pass'))
        self.assertEqual(e._player(0)['gold']-before,20)
        self.assertEqual(e.state['phase'],'final')
        e.apply(0,dict(type='pass'))
        self.assertEqual(e.state['phase'],'finished')


if __name__=='__main__':unittest.main()

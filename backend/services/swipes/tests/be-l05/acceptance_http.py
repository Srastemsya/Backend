from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import json
from pathlib import Path
import subprocess
import time
import unittest
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4


BASE = 'http://127.0.0.1:18195'
BACKEND = Path(__file__).resolve().parents[4]
COMPOSE = ('docker', 'compose', '-p', 'srastemsya_l05_tester_final',
           '-f', 'compose.yaml', '-f', 'compose.dev.yaml')
T = datetime.fromisoformat('2089-12-01T00:00:00+00:00')
MIX = {'kind': 'EVENT', 'localDate': '2090-02-01'}
SINGLE = {'kind': 'EVENT', 'categoryId': 'dev-lobby-two'}
LEGACY = {'kind': 'EVENT', 'categoryId': 'dev-swipe-events'}


def ids(room):
    return [card['ref']['id'] for card in room['round']['candidates']]


def refs(prefix, numbers):
    return [f'{prefix}-{number:02d}' for number in numbers]


def request(path, user=None, method='GET', body=None, status=200, error=None, minute=0):
    now = (T + timedelta(minutes=minute)).isoformat()
    headers = {'X-Dev-Swipes-Now': now, 'X-Dev-Catalog-Now': now}
    if user:
        headers['Authorization'] = 'Bearer ' + user['accessToken']
    if method == 'POST':
        headers['Idempotency-Key'] = str(uuid4())
    if body is not None:
        headers['Content-Type'] = 'application/json'
    req = Request(BASE + path, json.dumps(body).encode() if body is not None else None,
                  headers, method=method)
    try:
        response = urlopen(req, timeout=40)
    except HTTPError as exc:
        response = exc
    with response:
        raw = response.read()
        assert response.status == status, f'{method} {path}: HTTP {response.status}, expected {status}'
        if status == 204:
            assert not raw, f'{method} {path}: 204 with body'
            return None
        payload = json.loads(raw)
        if error:
            actual = payload.get('error', payload).get('code')
            assert actual == error, f'{method} {path}: {actual}, expected {error}'
        return payload


def api(path, *args, **kwargs):
    return request('/v1' + path, *args, **kwargs)


def sign_in(email):
    challenge = api('/auth/challenges', method='POST', status=201,
                    body={'channel': 'EMAIL', 'destination': email})
    return api('/auth/challenges/' + challenge['challengeId'] + '/verify',
               method='POST', body={'code': '0427'})


class Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.people = [sign_in(f'person{i}@example.test') for i in range(1, 11)]
        assert all(user['profileComplete'] for user in cls.people)
        cls.outsider = sign_in('new@example.test')

    def lobby(self):
        first = self.people[0]
        room = api('/rooms', first, 'POST', {}, 201)
        path = '/rooms/' + room['id']
        invite = api(path + '/invites', first, 'POST', {}, 201)
        token = parse_qs(urlparse(invite['url']).query)['token'][0]
        return path, token

    def start(self, count, filters):
        path, token = self.lobby()
        for person in self.people[1:count]:
            api('/room-invites/join', person, 'POST', {'token': token})
        room = api(path + '/start', self.people[0], 'POST', {'filters': filters})
        return path, token, room

    def get(self, path, person=0, **kwargs):
        return api(path, self.people[person], **kwargs)

    def round_path(self, path, room):
        return path + '/rounds/' + room['round']['id']

    def vote(self, path, person, card, choice='PASS', **kwargs):
        return api(path + '/votes/EVENT/' + card, self.people[person], 'PUT',
                   {'choice': choice}, **kwargs)

    def finish(self, path, person, **kwargs):
        return api(path + '/completion', self.people[person], 'PUT', **kwargs)

    def settle(self, path, minute=0):
        for _ in range(100):
            room = self.get(path, minute=minute)
            if room['state'] != 'REFRESHING':
                return room
            time.sleep(0.05)
        self.fail('REFRESHING did not settle')

    def vote_and_finish(self, path, room, count, likes=None, minute=0, concurrent=False):
        likes = likes or {}
        round_path = self.round_path(path, room)
        for person in range(count):
            for card in ids(room):
                self.vote(round_path, person, card, 'LIKE' if person < likes.get(card, 0)
                          else 'PASS', minute=minute)
        if concurrent:
            for person in range(count - 2):
                self.finish(round_path, person, minute=minute)
            with ThreadPoolExecutor(2) as pool:
                list(pool.map(lambda person: self.finish(round_path, person, minute=minute),
                              range(count - 2, count)))
        else:
            for person in range(count):
                self.finish(round_path, person, minute=minute)
        return self.settle(path, minute)

    def restart(self):
        subprocess.run((*COMPOSE, 'restart', 'swipes'), cwd=BACKEND, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(40):
            try:
                request('/swipes/health')
                return
            except (AssertionError, OSError):
                time.sleep(0.25)
        self.fail('swipes did not recover')

    def test_l05_01_02_03_05_weighting_and_concurrency(self):
        path, _, first = self.start(5, MIX)
        self.assertEqual(ids(first), refs('dev-lobby-mix', range(1, 11)))
        self.assertEqual(first['round']['number'], 1)
        second = self.vote_and_finish(path, first, 5, {card: 3 for card in ids(first)[::2]},
                                      concurrent=True)
        expected_second = refs('dev-lobby-mix', (11, 14, 17, 20, 23, 26, 29, 32, 35, 13))
        self.assertEqual(ids(second), expected_second)
        self.assertEqual(second['round']['number'], 2)
        self.assertIsNone(second['result'])
        before = [self.get(path, person) for person in range(5)]
        self.assertTrue(all(s['round'] == second['round'] for s in before))
        self.restart()
        self.assertEqual([self.get(path, person) for person in range(5)], before)
        # A scored +5 in round one and -45 in round two. B scored -25
        # in round one only. C scored -5 in round two only. Thus C>B>A,
        # whereas weighting just round two would order B>C>A.
        third = self.vote_and_finish(path, second, 5)
        self.assertEqual(third['round']['number'], 3)
        self.assertEqual(ids(third), refs('dev-lobby-mix', (16, 19, 22, 25, 28, 31, 34, 12, 15, 18)))

    def test_l05_04_single_category(self):
        path, _, first = self.start(5, SINGLE)
        self.assertEqual(ids(first), refs('dev-lobby-two', range(1, 11)))
        second = self.vote_and_finish(path, first, 5)
        self.assertEqual(ids(second), refs('dev-lobby-two', range(11, 15)))

    def test_l05_06_live_publication(self):
        path, _, first = self.start(5, MIX)
        event = api('/events', self.people[5], 'POST', {
            'title': 'BE-L05 catalog refresh', 'description': 'Acceptance fixture',
            'categoryId': 'dev-lobby-a', 'startsAt': '2090-02-01T00:13:30Z',
            'timeZone': 'Asia/Vladivostok', 'location': {
                'latitude': 43.11, 'longitude': 131.89, 'address': 'Vladivostok'},
            'admission': {'type': 'OPEN'}}, 201)
        self.assertEqual(event['organizerId'], self.people[5]['userId'])
        self.assertEqual(ids(self.get(path)), ids(first))
        second = self.vote_and_finish(path, first, 5, {card: 3 for card in ids(first)[::2]})
        expected = refs('dev-lobby-mix', (11, 14, 17, 20, 23, 26, 29, 32, 35))
        expected.insert(1, event['id'])
        self.assertEqual(ids(second), expected)

    def test_l04_round_expiry_and_recovery(self):
        path, _, first = self.start(5, SINGLE)
        self.assertEqual(datetime.fromisoformat(first['round']['expiresAt']), T + timedelta(minutes=30))
        second = self.vote_and_finish(path, first, 5, minute=20)
        active = self.get(path, minute=30)
        self.assertEqual(active['state'], 'VOTING')
        self.assertEqual(active['round']['id'], second['round']['id'])
        self.assertEqual(active['round']['number'], 2)
        self.assertEqual(datetime.fromisoformat(active['round']['expiresAt']), T + timedelta(minutes=50))
        rp = self.round_path(path, second)
        for card in ids(second):
            self.vote(rp, 0, card, minute=30)
        self.finish(rp, 0, minute=30)
        self.vote(rp, 1, ids(second)[0], 'LIKE', minute=30)
        before = [self.get(path, person, minute=30) for person in range(5)]
        self.assertTrue(before[0]['round']['myFinished'])
        self.assertEqual(len(before[0]['round']['myVotes']), len(ids(second)))
        self.assertFalse(before[1]['round']['myFinished'])
        self.assertEqual(before[1]['round']['myVotes'][0]['choice'], 'LIKE')
        self.restart()
        self.assertEqual([self.get(path, person, minute=30) for person in range(5)], before)
        closed = self.get(path, minute=50)
        self.assertEqual((closed['state'], closed['round'], closed['result']), ('CLOSED', None, None))
        self.vote(rp, 1, ids(second)[0], minute=50, status=409)
        self.finish(rp, 1, minute=50, status=409)
        self.assertEqual(self.get(path, minute=50), closed)

    def test_l03_threshold_boundaries_and_result(self):
        for count, threshold in ((2, 2), (3, 3), (5, 4), (10, 7)):
            with self.subTest(count=count):
                path, _, first = self.start(count, SINGLE)
                self.assertIsNone(first['result'])
                second = self.vote_and_finish(path, first, count, {ids(first)[0]: threshold - 1})
                self.assertEqual(second['state'], 'VOTING')
                self.assertEqual(second['round']['number'], 2)
                self.assertIsNone(second['result'])
                winner = ids(second)[0]
                result = self.vote_and_finish(path, second, count, {winner: threshold})
                self.assert_match(result, winner, threshold, count)

    def assert_match(self, room, winner, likes, count):
        self.assertEqual(room['state'], 'MATCHED')
        self.assertEqual(room['result'], {'winner': {'kind': 'EVENT', 'id': winner},
                                          'basis': 'THRESHOLD', 'likes': likes, 'memberCount': count})

    def test_l03_concurrent_winner_selection(self):
        for later_likes in (4, 5):
            with self.subTest(later_likes=later_likes):
                path, _, first = self.start(5, SINGLE)
                early, late = ids(first)[:2]
                result = self.vote_and_finish(path, first, 5, {early: 4, late: later_likes},
                                              concurrent=True)
                winner = early if later_likes == 4 else late
                for person in range(5):
                    snapshot = self.get(path, person)
                    self.assert_match(snapshot, winner, later_likes, 5)
                    self.assertEqual(snapshot['version'], result['version'])

    def test_l02_pool_pagination_and_exhaustion(self):
        page = self.get('/feed/candidates?' + urlencode(LEGACY))
        expected = refs('dev-swipe-event', range(1, 23))
        self.assertEqual([c['ref']['id'] for c in page['items']], expected[:20])
        self.assertTrue(page['nextCursor'])
        path, _, room = self.start(4, LEGACY)
        for index in range(3):
            self.assertEqual(room['round']['number'], index + 1)
            self.assertEqual(ids(room), expected[10 * index:10 * (index + 1)])
            for person in range(4):
                snapshot = self.get(path, person)
                self.assertEqual(snapshot['round'], room['round'])
                self.assertEqual(snapshot['members'], room['members'])
            room = self.vote_and_finish(path, room, 4)
        self.assertEqual((room['state'], room['round'], room['result']), ('EXHAUSTED', None, None))

    def test_d03_privacy_completion_and_reconnect(self):
        path, token, room = self.start(4, SINGLE)
        # The separate outside account has an incomplete profile for INT-01.
        self.get(path, 4, status=404, error='NOT_FOUND')
        api('/room-invites/join', self.people[4], 'POST', {'token': token}, 409)
        rp = self.round_path(path, room)
        self.finish(rp, 0, status=409, error='INVALID_STATE')
        cards = ids(room)
        for card in cards:
            self.vote(rp, 0, card)
        self.vote(rp, 0, cards[0], 'LIKE')
        self.finish(rp, 0)
        self.vote(rp, 0, cards[0], status=409)
        snapshot = self.get(path)
        self.assertTrue(snapshot['round']['myFinished'])
        votes = {vote['candidate']['id']: vote['choice'] for vote in snapshot['round']['myVotes']}
        self.assertEqual(votes, dict.fromkeys(cards, 'PASS') | {cards[0]: 'LIKE'})
        self.assertEqual(self.get(path, 1)['round']['myVotes'], [])

    def poll(self, path, version, seconds=25):
        return f'{path}?afterVersion={version}&waitSeconds={seconds}'

    def test_d03_long_poll_join_and_vote(self):
        path, token = self.lobby()
        initial = self.get(path)
        with ThreadPoolExecutor() as pool:
            waiting = pool.submit(self.get, self.poll(path, initial['version']))
            time.sleep(0.5)
            self.assertFalse(waiting.done())
            api('/room-invites/join', self.people[1], 'POST', {'token': token})
            joined = waiting.result()
        self.assertGreater(joined['version'], initial['version'])
        self.assertEqual(len(joined['members']), 2)
        self.assertNotIn(token, json.dumps(joined))
        room = api(path + '/start', self.people[0], 'POST', {'filters': SINGLE})
        query = self.poll(path, room['version'])
        with ThreadPoolExecutor() as pool:
            waiting = pool.submit(self.get, query)
            time.sleep(0.5)
            self.assertFalse(waiting.done())
            self.vote(self.round_path(path, room), 1, ids(room)[0], 'LIKE')
            updated = waiting.result()
        self.assertGreater(updated['version'], room['version'])
        self.assertEqual(updated['round']['myVotes'], [])
        start = time.monotonic()
        self.assertEqual(self.get(query), updated)
        self.assertLess(time.monotonic() - start, 2)

    def test_z_d03_timeout_and_revocation(self):
        # Owner of this room is account 10, whose token is disposable here.
        owner = self.people[9]
        room = api('/rooms', owner, 'POST', {}, 201)
        path = '/rooms/' + room['id']
        query = self.poll(path, room['version'])
        start = time.monotonic()
        api(query, owner, status=204)
        self.assertGreaterEqual(time.monotonic() - start, 24)
        api(self.poll(path, room['version'], 1), owner, status=204)
        start = time.monotonic()
        self.get(query, status=404, error='NOT_FOUND')
        self.assertLess(time.monotonic() - start, 2)
        with ThreadPoolExecutor() as pool:
            waiting = pool.submit(api, self.poll(path, room['version'], 3), owner,
                                  status=401)
            time.sleep(0.5)
            self.assertFalse(waiting.done())
            api('/auth/session', owner, 'DELETE', status=204)
            waiting.result()

    def test_int01_authorization(self):
        api('/feed/candidates?kind=EVENT', status=401, error='UNAUTHENTICATED')
        api('/rooms', method='POST', body={}, status=401, error='UNAUTHENTICATED')
        self.assertFalse(self.outsider['profileComplete'])
        api('/feed/candidates?kind=EVENT', self.outsider, status=403, error='PROFILE_INCOMPLETE')
        api('/rooms', self.outsider, 'POST', {}, 403, error='PROFILE_INCOMPLETE')

    def test_int02_swipes_health_database_recovery(self):
        request('/swipes/health')
        since = datetime.now().astimezone().isoformat(timespec='seconds')
        try:
            subprocess.run((*COMPOSE, 'stop', 'swipes-db'), cwd=BACKEND, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            unhealthy = request('/swipes/health', status=503)
        finally:
            subprocess.run((*COMPOSE, 'up', '-d', '--wait', 'swipes-db'), cwd=BACKEND, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        healthy = request('/swipes/health')
        logs = subprocess.check_output((*COMPOSE, 'logs', '--no-color', '--since', since, 'swipes'),
                                       cwd=BACKEND, stderr=subprocess.DEVNULL, text=True)
        evidence = json.dumps([unhealthy, healthy]) + logs
        import re
        self.assertFalse(bool(re.search(r'(?:postgres(?:ql)?(?:\+\w+)?://[^\s/@]+:[^\s/@]+@|password\s*[=:]\s*\S+)',
                                        evidence, re.IGNORECASE)),
                         'credential-shaped string in health response or swipes logs')

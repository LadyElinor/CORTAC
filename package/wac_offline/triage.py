"""Optional v1 bounded complaint triage for a trusted synthetic harness.

This subclasses the legacy disposable SQLite gateway, reusing its proposal,
receipt, policy, evidence and mandate checks. It is NOT an authentication or
production security boundary. All authority and controller facts are fabricated,
constructor-pinned declarations. There are no network, model, credential or
arbitrary filesystem operations. Caller-supplied identities are not authenticated.
"""
from copy import deepcopy
import json

from .runner import (ScratchGateway, RunnerError, SCOPE, digest, exact, integer,
                     sha, text)

CONFIG_FIELDS = ('schema', 'evidence_digest', 'ordinary_budget', 'repair_budget',
                 'complaints', 'work_items')
SLOT_FIELDS = ('id', 'claimant', 'work_item_id', 'evidence_ids', 'reason',
               'duplicate_of', 'appeals', 'factfinding_budget', 'review_budget')
ITEM_FIELDS = ('id', 'proposal_digest', 'expected_revision', 'operation',
               'mandate_id', 'executor', 'complaint_ids', 'audit_budget')
GRANT_FIELDS = ('schema', 'id', 'case_id', 'policy_digest', 'triage_digest',
                'epoch', 'action', 'actor', 'authorizer', 'expected_revision',
                'expires_tick', 'max_uses', 'complaints', 'work_item_id',
                'proposal_digest', 'finding', 'scope', 'provenance')
ACTIONS = {'FACT_FINDING': 'assessor', 'REVIEW': 'reviewer', 'AUDIT': 'auditor'}


def _ids(value, label, nonempty=False):
    if type(value) is not list or (nonempty and not value):
        raise RunnerError(label + ': list required')
    if any(type(i) is not str or not i.strip() for i in value) or len(set(value)) != len(value):
        raise RunnerError(label + ': invalid or duplicate IDs')
    if value != sorted(value):
        raise RunnerError(label + ': canonical ID order required')


def _slot(config, identifier):
    text(identifier, 'complaint ID')
    slots = [s for s in config['complaints'] if s['id'] == identifier]
    if len(slots) != 1:
        raise RunnerError('unknown complaint slot')
    return slots[0]


def complaint_binding(config, identifier, version=0):
    """Pure helper binding the exact pinned complaint statement, not its truth."""
    slot = _slot(config, identifier)
    integer(version, 'complaint version')
    if version > len(slot['appeals']):
        raise RunnerError('unknown complaint version')
    statement = slot if version == 0 else slot['appeals'][version - 1]
    spec = dict(id=identifier, version=version, claimant=slot['claimant'],
                work_item_id=slot['work_item_id'], duplicate_of=slot['duplicate_of'],
                evidence_ids=statement['evidence_ids'], reason=statement['reason'])
    return dict(id=identifier, version=version, binding_digest=digest('ComplaintSpec', spec))


def make_grant(identifier, action, actor, authorizer, policy, config, *,
               complaint_versions=None, work_item_id=None, expected_revision,
               expires_tick=1000, finding=None):
    """Construct a grant; only constructor-pinned exact bytes convey test authority.

    ``complaint_versions`` is an ID-to-version mapping (versions start at zero).
    Merely calling this helper after construction cannot create authority.
    """
    versions = {} if complaint_versions is None else complaint_versions
    if type(versions) is not dict:
        raise RunnerError('complaint_versions must be a mapping')
    items = [w for w in config['work_items'] if w['id'] == work_item_id]
    if work_item_id is not None and len(items) != 1:
        raise RunnerError('unknown work item')
    return dict(schema='cortac.scratch.triage.grant.v1', id=identifier,
                case_id=policy['case_id'], policy_digest=digest('Policy', policy),
                triage_digest=digest('TriageConfig', config), epoch=policy['epoch'],
                action=action, actor=actor, authorizer=authorizer,
                expected_revision=expected_revision, expires_tick=expires_tick,
                max_uses=1, complaints=[complaint_binding(config, i, versions[i]) for i in sorted(versions)],
                work_item_id=work_item_id, proposal_digest=items[0]['proposal_digest'] if items else None,
                finding=deepcopy(finding), scope=SCOPE, provenance='SYNTHETIC_FIXTURE')


class TriageGateway(ScratchGateway):
    """Serialized optional versioned gateway with strictly partitioned resources.

    The sum of the constructor-known pool limits cannot exceed the legacy policy
    operation budget. Batch review spends one unit in EACH distinct root complaint
    account. Duplicate aliases receive no new reserve and cannot borrow a different
    root account. All admitted attempts, including rejection, spend their own pool;
    at-cap attempts append an explicit INCOMPLETE record without changing holds.
    This is a finite worklist allocation, not Sybil resistance or unbounded fairness.
    """
    def __init__(self, policy, evidence, mandates, *, triage_config, grants):
        super().__init__(policy, evidence, mandates)
        try:
            self._config = deepcopy(triage_config)
            self._triage_digest = digest('TriageConfig', self._config)
            self._validate_config()
            self._grants = {}
            if type(grants) is not list:
                raise RunnerError('grants must be a list')
            for grant in deepcopy(grants):
                self._validate_grant(grant)
                if grant['id'] in self._grants:
                    raise RunnerError('duplicate triage grant ID')
                self._grants[grant['id']] = grant
            state = self.snapshot()
            state.update(triage_schema='cortac.scratch.triage.state.v1',
                         complaints={}, budgets=deepcopy(self._budget_limits),
                         incomplete=[], used_grants=[], revoked_grants={},
                         factfinding_records=[], review_records={}, audit_records=[],
                         activity_participants=[], work_item_effects={})
            with self._db:
                self._db.execute('UPDATE state SET body=? WHERE id=1', (json.dumps(state),))
        except Exception:
            self.close()
            raise

    def _validate_config(self):
        c = self._config
        exact(c, CONFIG_FIELDS, 'triage config')
        if c['schema'] != 'cortac.scratch.triage.config.v1':
            raise RunnerError('unsupported triage config schema')
        sha(c['evidence_digest'], 'triage evidence digest')
        if c['evidence_digest'] != digest('TriageEvidence', sorted(self._evidence.values(), key=lambda e: e['id'])):
            raise RunnerError('triage evidence inventory mismatch')
        for field in ('ordinary_budget', 'repair_budget'):
            integer(c[field], field)
        if type(c['complaints']) is not list or type(c['work_items']) is not list or not c['work_items']:
            raise RunnerError('bounded complaint/work item lists required')
        self._slots = {}; self._items = {}
        self._budget_limits = {key: dict(limit=c[key + '_budget'], used=0) for key in ('ordinary', 'repair')}
        for item in c['work_items']:
            exact(item, ITEM_FIELDS, 'work item')
            text(item['id'], 'work item ID'); sha(item['proposal_digest'], 'proposal digest')
            integer(item['expected_revision'], 'work item revision')
            integer(item['audit_budget'], 'audit budget')
            if item['operation'] not in ('COMMIT', 'REPAIR'):
                raise RunnerError('invalid work item operation')
            if (item['operation'] == 'COMMIT') != (item['expected_revision'] == 0):
                raise RunnerError('work item operation/revision mismatch')
            text(item['mandate_id'], 'mandate ID')
            if item['mandate_id'] not in self._mandates or self._mandates[item['mandate_id']]['proposal_digest'] != item['proposal_digest']:
                raise RunnerError('work item mandate mismatch')
            self._actor(item['executor'], 'executor')
            _ids(item['complaint_ids'], 'work item complaints')
            if item['operation'] == 'COMMIT' and item['complaint_ids']:
                raise RunnerError('initial work item cannot resolve complaints')
            if item['id'] in self._items:
                raise RunnerError('duplicate work item')
            self._items[item['id']] = item
            self._budget_limits['audit:' + item['id']] = dict(limit=item['audit_budget'], used=0)
        for slot in c['complaints']:
            exact(slot, SLOT_FIELDS, 'complaint slot')
            for field in ('id', 'claimant', 'work_item_id', 'reason'):
                text(slot[field], field)
            if slot['id'] in self._slots or slot['work_item_id'] not in self._items:
                raise RunnerError('duplicate complaint slot or unknown work item')
            self._validate_evidence_ids(slot['evidence_ids'])
            for field in ('factfinding_budget', 'review_budget'):
                integer(slot[field], field)
            if type(slot['appeals']) is not list:
                raise RunnerError('appeals must be a bounded list')
            for appeal in slot['appeals']:
                exact(appeal, ('evidence_ids', 'reason'), 'appeal specification')
                self._validate_evidence_ids(appeal['evidence_ids']); text(appeal['reason'], 'appeal reason')
            if slot['duplicate_of'] is not None:
                text(slot['duplicate_of'], 'duplicate root')
                if slot['factfinding_budget'] or slot['review_budget']:
                    raise RunnerError('duplicate aliases cannot acquire new reserves')
            else:
                for name in ('factfinding', 'review'):
                    self._budget_limits[name + ':' + slot['id']] = dict(limit=slot[name + '_budget'], used=0)
            self._budget_limits['intake:' + slot['id']] = dict(limit=1 + len(slot['appeals']), used=0)
            self._slots[slot['id']] = slot
        for slot in self._slots.values():
            root = slot['duplicate_of']
            if root is not None:
                if root not in self._slots or self._slots[root]['duplicate_of'] is not None or root == slot['id']:
                    raise RunnerError('duplicate must reference one known original slot')
                if self._slots[root]['work_item_id'] != slot['work_item_id']:
                    raise RunnerError('duplicate must reference the same work item')
        for item in self._items.values():
            if any(i not in self._slots for i in item['complaint_ids']):
                raise RunnerError('work item has unknown complaint slot')
        if sum(b['limit'] for b in self._budget_limits.values()) > self._policy['operation_budget']:
            raise RunnerError('partitioned budgets exceed policy operation budget')

    def _validate_evidence_ids(self, ids):
        _ids(ids, 'evidence IDs', nonempty=True)
        if any(i not in self._evidence for i in ids):
            raise RunnerError('unresolved evidence')

    def _validate_grant(self, g):
        exact(g, GRANT_FIELDS, 'triage grant')
        if g['schema'] != 'cortac.scratch.triage.grant.v1' or g['scope'] != SCOPE or g['provenance'] != 'SYNTHETIC_FIXTURE':
            raise RunnerError('unsupported triage grant scope/schema')
        text(g['id'], 'grant ID')
        if g['case_id'] != self._policy['case_id'] or g['policy_digest'] != self._policy_digest or g['triage_digest'] != self._triage_digest:
            raise RunnerError('triage grant policy/config mismatch')
        integer(g['epoch'], 'grant epoch', 1); integer(g['expected_revision'], 'grant revision')
        integer(g['expires_tick'], 'grant expiry', 1)
        if g['epoch'] != self._policy['epoch'] or type(g['max_uses']) is not int or g['max_uses'] != 1:
            raise RunnerError('triage grant epoch/single-use mismatch')
        if type(g['action']) is not str or g['action'] not in ACTIONS:
            raise RunnerError('unsupported triage grant action')
        self._actor(g['actor'], ACTIONS[g['action']]); self._actor(g['authorizer'], 'authorizer')
        self._independent(g['actor'], [g['authorizer']] + self._policy['excluded_ids'])
        if type(g['complaints']) is not list:
            raise RunnerError('grant complaints must be a list')
        ids = []
        for binding in g['complaints']:
            exact(binding, ('id', 'version', 'binding_digest'), 'grant complaint binding')
            if binding != complaint_binding(self._config, binding['id'], binding['version']):
                raise RunnerError('grant complaint binding mismatch')
            ids.append(binding['id'])
        _ids(ids, 'grant complaint IDs')
        if g['action'] == 'FACT_FINDING':
            if len(ids) != 1 or g['work_item_id'] is not None or g['proposal_digest'] is not None:
                raise RunnerError('factfinding must target one complaint only')
            f = g['finding']
            exact(f, ('status', 'controller', 'evidence_ids'), 'finding')
            if f['status'] not in ('UNRESOLVED', 'DECLARED_CONTROLLER'):
                raise RunnerError('unsupported finding')
            if f['status'] == 'UNRESOLVED':
                if f['controller'] is not None:
                    raise RunnerError('unresolved finding cannot declare controller')
            else:
                text(f['controller'], 'declared controller')
            _ids(f['evidence_ids'], 'finding evidence IDs', nonempty=f['status'] == 'DECLARED_CONTROLLER')
            if any(i not in self._evidence for i in f['evidence_ids']):
                raise RunnerError('finding evidence unresolved')
        else:
            if g['finding'] is not None or type(g['work_item_id']) is not str or g['work_item_id'] not in self._items:
                raise RunnerError('review/audit must target one work item')
            item = self._items[g['work_item_id']]
            if g['proposal_digest'] != item['proposal_digest'] or ids != item['complaint_ids']:
                raise RunnerError('grant work item/complaint mismatch')
            wanted = item['expected_revision'] + (g['action'] == 'AUDIT')
            if g['expected_revision'] != wanted:
                raise RunnerError('grant work item revision mismatch')
            if g['action'] == 'REVIEW' and (item['operation'] != 'REPAIR' or not ids):
                raise RunnerError('review requires repair complaints')

    def _root(self, identifier):
        text(identifier, 'complaint ID')
        if identifier not in self._slots:
            raise RunnerError('unknown complaint slot')
        return self._slots[identifier]['duplicate_of'] or identifier

    def _run(self, action, operation):
        # The inherited mandate revocation method routes only to ordinary work.
        def recorded(state):
            result = operation(state)
            if action == 'revoke':
                self._remember(state, [result['actor']])
            return result
        return self._run_budget(action, ['ordinary'], recorded)

    def _run_budget(self, action, keys, operation):
        keys = sorted(set(keys))
        with self._lock, self._db:
            state = self.snapshot()
            if any(k not in state['budgets'] for k in keys) or not keys:
                raise RunnerError('unknown or empty budget partition')
            exhausted = [k for k in keys if state['budgets'][k]['used'] >= state['budgets'][k]['limit']]
            if exhausted:
                # At most one persisted exhaustion marker per finite pool. Later
                # at-cap attempts do not create free unbounded journal growth.
                reported = {key for r in state['incomplete'] for key in r['exhausted']}
                new = [key for key in exhausted if key not in reported]
                if new:
                    record = dict(action=action, result='INCOMPLETE', reason='partition budget exhausted',
                                  exhausted=new, tick=state['tick'], revision=state['revision'])
                    state['incomplete'].append(record)
                    state['journal'].append(record)
                    self._db.execute('UPDATE state SET body=? WHERE id=1', (json.dumps(state),))
                error = RunnerError('INCOMPLETE: partition budget exhausted: ' + ', '.join(exhausted))
            else:
                state['tick'] += 1
                for key in keys:
                    state['budgets'][key]['used'] += 1
                changed = deepcopy(state)
                try:
                    result = operation(changed)
                except (ValueError, TypeError, KeyError) as exc:
                    state['journal'].append(dict(tick=state['tick'], action=action, budgets=keys,
                                                 result='REJECTED', reason=str(exc)))
                    self._db.execute('UPDATE state SET body=? WHERE id=1', (json.dumps(state),))
                    error = RunnerError(str(exc))
                else:
                    changed['journal'].append(dict(tick=changed['tick'], action=action, budgets=keys,
                                                   result='ACCEPTED', result_digest=digest('Result', result)))
                    self._db.execute('UPDATE state SET body=? WHERE id=1', (json.dumps(changed),))
                    error = None
        if error:
            raise error
        return deepcopy(result)

    def _history(self, state):
        return sorted(set(state['participants'] + state['activity_participants']))

    def _remember(self, state, actors):
        state['activity_participants'] = sorted(set(state['activity_participants'] + actors))

    def _grant(self, state, identifier, action, actor, consume=True):
        text(identifier, 'grant ID')
        if identifier not in self._grants:
            raise RunnerError('unknown triage grant')
        g = self._grants[identifier]
        if g['action'] != action or g['actor'] != actor:
            raise RunnerError('triage grant action/actor mismatch')
        self._actor(actor, ACTIONS[action])
        if identifier in state['revoked_grants']:
            raise RunnerError('triage grant revoked')
        if g['epoch'] != self._policy['epoch'] or g['expected_revision'] != state['revision'] or state['tick'] >= g['expires_tick']:
            raise RunnerError('triage grant stale or expired')
        if consume and identifier in state['used_grants']:
            raise RunnerError('triage grant already consumed')
        return g

    def _protected(self, action, actor, grant_id, select, operation):
        """Only exact, live pinned scope may debit its protected allocation.

        Invalid routing/authority attempts use ordinary work. The lock spans
        preflight and the admitted transaction; no competing revocation can slip
        between them. Role names are still unauthenticated harness assertions.
        """
        with self._lock:
            try:
                state = self.snapshot()
                grant = self._grant(state, grant_id, action, actor)
                keys = select(grant, state)
            except (ValueError, TypeError, KeyError) as exc:
                message = str(exc)
                def rejected(_state):
                    raise RunnerError(message)
                return self._run_budget(action.lower(), ['ordinary'], rejected)
            return self._preflight_budget(action.lower(), keys, operation)

    def _preflight_budget(self, action, keys, operation):
        # These callbacks only transform a supplied in-memory state. Reuse the
        # exact transition on a discarded copy to validate the entire request,
        # including versions/controllers/effect bytes, before protected debit.
        # The actual metered transition rechecks inside the same lock. Invalid
        # traffic can exhaust ordinary work, never a protected/intake allocation.
        with self._lock:
            preview = self.snapshot()
            preview['tick'] += 1
            try:
                operation(preview)
            except (ValueError, TypeError, KeyError) as exc:
                message = str(exc)
                def rejected(_state):
                    raise RunnerError(message)
                return self._run_budget(action, ['ordinary'], rejected)
            return self._run_budget(action, keys, operation)

    def _claimant_independence(self, state, actor, identifiers, require_known=True):
        controller = self._principals[actor]['controller']
        for identifier in identifiers:
            c = state['complaints'][identifier]
            if require_known and c['controller'] is None:
                raise RunnerError('FACT_FINDING_REQUIRED: claimant controller unknown; hold preserved')
            if c['controller'] == controller:
                raise RunnerError('actor shares declared claimant controller')

    def _support_independence(self, state, grant, identifiers):
        self._independent(grant['authorizer'], self._history(state) + self._policy['excluded_ids'])
        self._claimant_independence(state, grant['authorizer'], identifiers, require_known=False)

    def _bindings(self, state, identifiers):
        records = []
        for identifier in identifiers:
            if identifier not in state['complaints']:
                raise RunnerError('complaint not lodged')
            c = state['complaints'][identifier]
            records.append(dict(complaint_binding(self._config, identifier, c['version']),
                                complaint_digest=c['current_digest']))
        return records

    def _grant_bindings(self, bindings):
        return [{k: b[k] for k in ('id', 'version', 'binding_digest')} for b in bindings]

    def _held(self, state):
        return sorted(i for i, c in state['complaints'].items() if c['hold'])

    def issue(self, proposal, kind, actor):
        p = deepcopy(proposal)
        def issue(state):
            self._proposal(p, state)
            if kind not in ('ASSESSMENT', 'APPROVAL', 'AUTHORIZATION'):
                raise RunnerError('unsupported receipt kind')
            role = {'ASSESSMENT': 'assessor', 'APPROVAL': 'approver', 'AUTHORIZATION': 'authorizer'}[kind]
            self._actor(actor, role)
            self._independent(actor, [p['proposer']] + self._policy['excluded_ids'])
            if kind == 'APPROVAL' and actor not in self._policy['approval_ids']:
                raise RunnerError('actor outside frozen approval roll')
            receipt = self._make_receipt(p, kind, actor, state)
            self._remember(state, [actor, p['proposer']])
            return receipt
        key = 'repair' if type(p) is dict and p.get('operation') == 'REPAIR' else 'ordinary'
        return self._run_budget('issue_' + str(kind), [key], issue)

    def challenge(self, *args, **kwargs):
        """Legacy spelling is an alias, never an unreserved bypass."""
        return self.lodge(*args, **kwargs)

    def lodge(self, identifier, claimant, effect, evidence_ids, reason, duplicate_of=None):
        effect, evidence_ids = deepcopy(effect), deepcopy(evidence_ids)
        def lodge(state):
            slot = _slot(self._config, identifier)
            if identifier in state['complaints']:
                raise RunnerError('duplicate complaint ID')
            if (claimant != slot['claimant'] or evidence_ids != slot['evidence_ids'] or
                    reason != slot['reason'] or duplicate_of != slot['duplicate_of']):
                raise RunnerError('complaint differs from pinned slot')
            if not state['effects'] or digest('Effect', effect) != digest('Effect', state['effects'][-1]):
                raise RunnerError('complaint requires current exact effect')
            if effect['work_item_id'] != slot['work_item_id']:
                raise RunnerError('complaint work item mismatch')
            if duplicate_of is not None and duplicate_of not in state['complaints']:
                raise RunnerError('duplicate original must be lodged first')
            record = self._version_record(slot, 0, effect)
            controller = self._principals.get(claimant, {}).get('controller')
            c = dict(id=identifier, claimant=claimant, duplicate_of=duplicate_of,
                     versions=[record], version=0, current_digest=record['digest'], hold=True,
                     appeal_status='READY_FOR_REVIEW' if controller else 'FACT_FINDING_REQUIRED',
                     resolution=None, controller=controller,
                     controller_basis='PINNED_PRINCIPAL' if controller else 'UNKNOWN',
                     findings=[], appeals=[], resolutions=[])
            state['complaints'][identifier] = c
            return c
        text(identifier, 'complaint ID')
        return self._preflight_budget('lodge', ['intake:' + identifier], lodge)

    def _version_record(self, slot, version, effect):
        statement = slot if version == 0 else slot['appeals'][version - 1]
        record = dict(schema='cortac.scratch.triage.complaint.v1', id=slot['id'],
                      claimant=slot['claimant'], duplicate_of=slot['duplicate_of'], version=version,
                      case_id=self._policy['case_id'], work_item_id=slot['work_item_id'],
                      effect_digest=digest('Effect', effect),
                      evidence=[dict(id=i, digest=digest('Evidence', self._evidence[i])) for i in statement['evidence_ids']],
                      reason=statement['reason'], scope=SCOPE, provenance='SYNTHETIC_FIXTURE')
        return dict(record, digest=digest('ComplaintVersion', record))

    def appeal(self, identifier, claimant, evidence_ids, reason):
        evidence_ids = deepcopy(evidence_ids)
        def appeal(state):
            slot = _slot(self._config, identifier)
            if identifier not in state['complaints'] or claimant != slot['claimant']:
                raise RunnerError('appeal claimant/complaint mismatch')
            c = state['complaints'][identifier]; version = c['version'] + 1
            if version > len(slot['appeals']):
                raise RunnerError('bounded appeal capacity exhausted')
            statement = slot['appeals'][version - 1]
            if evidence_ids != statement['evidence_ids'] or reason != statement['reason']:
                raise RunnerError('appeal differs from pinned version')
            targets = [e for e in state['effects'] if digest('Effect', e) == c['versions'][0]['effect_digest']]
            if len(targets) != 1:
                raise RunnerError('appeal original effect unavailable')
            target = targets[0]
            record = self._version_record(slot, version, target)
            c['versions'].append(record); c['appeals'].append(record)
            c['version'] = version; c['current_digest'] = record['digest']; c['hold'] = True
            c['resolution'] = None
            c['appeal_status'] = 'READY_FOR_REVIEW' if c['controller'] else 'FACT_FINDING_REQUIRED'
            return c
        text(identifier, 'complaint ID')
        return self._preflight_budget('appeal', ['intake:' + identifier], appeal)

    def factfind(self, complaint_id, actor, grant_id):
        root = self._root(complaint_id)
        def factfind(state):
            g = self._grant(state, grant_id, 'FACT_FINDING', actor)
            bindings = self._bindings(state, [complaint_id])
            if g['complaints'] != self._grant_bindings(bindings):
                raise RunnerError('factfinding complaint/version mismatch')
            c = state['complaints'][complaint_id]
            if not c['hold'] or c['controller'] is not None:
                raise RunnerError('factfinding cannot replace an existing controller declaration')
            history = self._history(state)
            # Same-case continuation after an UNRESOLVED finding is permitted;
            # participation in any other role/case still disqualifies the finder.
            previous = [f for f in state['factfinding_records'] if f['actor'] == actor]
            other_roles = (actor in state['participants'] or
                           any(r['actor'] == actor for r in state['receipts'].values()))
            if previous and not other_roles and all(f['complaint_id'] == complaint_id and f['result'] == 'UNRESOLVED' for f in previous):
                history = [a for a in history if a != actor]
            self._independent(actor, history + self._policy['excluded_ids'] + [g['authorizer']])
            self._support_independence(state, g, [complaint_id])
            finding = g['finding']; controller = finding['controller']
            if controller == self._principals[g['authorizer']]['controller']:
                raise RunnerError('factfinding authorizer shares declared claimant controller')
            if controller == self._principals[actor]['controller']:
                raise RunnerError('factfinder shares declared claimant controller')
            declarations = {other['controller'] for other in state['complaints'].values()
                            if other['claimant'] == c['claimant'] and other['controller'] is not None}
            if controller is not None and declarations and declarations != {controller}:
                raise RunnerError('cannot overwrite another complaint declaration for the same claimant')
            result = dict(schema='cortac.scratch.triage.finding.v1', complaint_id=complaint_id,
                          version=c['version'], complaint_digest=c['current_digest'], actor=actor,
                          grant_id=grant_id, grant_digest=digest('TriageGrant', g),
                          result=finding['status'], controller=controller,
                          evidence=[dict(id=i, digest=digest('Evidence', self._evidence[i])) for i in finding['evidence_ids']],
                          independence='DECLARED_CONTROLLER_CHECKED' if controller else 'CLAIMANT_CONTROLLER_UNKNOWN',
                          authority='NONE', controller_closure='SUPPLIED_UNVERIFIED',
                          scope=SCOPE, provenance='SYNTHETIC_FIXTURE')
            c['findings'].append(result); state['factfinding_records'].append(result)
            if controller is not None:
                c['controller'] = controller; c['controller_basis'] = 'PINNED_FACTFINDING_DECLARATION'
                c['appeal_status'] = 'READY_FOR_REVIEW'
            state['used_grants'].append(grant_id); self._remember(state, [actor])
            return result
        def select(g, state):
            if g['complaints'] != self._grant_bindings(self._bindings(state, [complaint_id])):
                raise RunnerError('factfinding complaint/version mismatch')
            return ['factfinding:' + root]
        return self._protected('FACT_FINDING', actor, grant_id, select, factfind)

    def _review_independence(self, state, actor, identifiers, others):
        self._independent(actor, others + self._policy['excluded_ids'])
        self._claimant_independence(state, actor, list(state['complaints']), require_known=False)
        controller = self._principals[actor]['controller']
        for identifier in identifiers:
            c = state['complaints'][identifier]
            if c['controller'] is None:
                raise RunnerError('FACT_FINDING_REQUIRED: claimant controller unknown; hold preserved')
            if controller == c['controller']:
                raise RunnerError('reviewer shares declared claimant controller')

    def review(self, complaint_ids, proposal, actor, grant_id):
        ids, p = deepcopy(complaint_ids), deepcopy(proposal)
        _ids(ids, 'review complaint IDs', nonempty=True)
        roots = sorted({self._root(i) for i in ids})
        def review(state):
            self._proposal(p, state)
            g = self._grant(state, grant_id, 'REVIEW', actor)
            item = self._items[g['work_item_id']]
            if p['operation'] != 'REPAIR' or g['proposal_digest'] != digest('Proposal', p):
                raise RunnerError('review proposal mismatch')
            if ids != self._held(state) or ids != item['complaint_ids']:
                raise RunnerError('review must bind ALL current holds')
            bindings = self._bindings(state, ids)
            if g['complaints'] != self._grant_bindings(bindings):
                raise RunnerError('review complaint/version mismatch')
            self._support_independence(state, g, ids)
            self._review_independence(state, actor, ids,
                                      self._history(state) + [p['proposer'], item['executor'], g['authorizer']])
            refs = {(r['id'], r['digest']) for r in p['evidence']}
            for identifier in ids:
                c = state['complaints'][identifier]
                if not all((r['id'], r['digest']) in refs for version in c['versions'] for r in version['evidence']):
                    raise RunnerError('repair omits complaint evidence')
            receipt = self._make_receipt(p, 'REVIEW', actor, state, digest('ComplaintBindings', bindings))
            state['review_records'][receipt['id']] = dict(grant_id=grant_id,
                grant_digest=digest('TriageGrant', g), work_item_id=item['id'],
                bindings=bindings, actor=actor, receipt_digest=digest('Receipt', receipt))
            for identifier in ids:
                state['complaints'][identifier]['appeal_status'] = 'REVIEWED_PENDING_REPAIR'
            state['used_grants'].append(grant_id); self._remember(state, [actor])
            return receipt
        def select(g, state):
            if [b['id'] for b in g['complaints']] != ids or g['proposal_digest'] != digest('Proposal', p):
                raise RunnerError('review request outside pinned grant scope')
            return ['review:' + root for root in roots]
        return self._protected('REVIEW', actor, grant_id, select, review)

    def _work_item(self, identifier, p, mandate_id, executor):
        text(identifier, 'work item ID')
        if identifier not in self._items:
            raise RunnerError('unknown work item')
        item = self._items[identifier]
        if (item['proposal_digest'] != digest('Proposal', p) or item['expected_revision'] != p['expected_revision'] or
                item['operation'] != p['operation'] or item['mandate_id'] != mandate_id or item['executor'] != executor):
            raise RunnerError('exact pinned work item mismatch')
        return item

    def commit(self, proposal, receipts, mandate_id, executor, work_item_id):
        p, receipts = deepcopy(proposal), deepcopy(receipts)
        def commit(state):
            pd = self._proposal(p, state)
            item = self._work_item(work_item_id, p, mandate_id, executor)
            if state['pending_audit'] is not None:
                raise RunnerError('previous effect requires audit')
            groups, participants = self._receipts(receipts, p, state)
            self._actor(executor, 'executor')
            self._independent(executor, participants + self._policy['excluded_ids'])
            if mandate_id in state['revoked_mandates']:
                raise RunnerError('mandate revoked')
            grant = self._mandates[mandate_id]
            authorizer = groups['AUTHORIZATION'][0]['actor']
            if grant['proposal_digest'] != pd or grant['authorizer'] != authorizer or state['tick'] >= grant['expires_tick']:
                raise RunnerError('mandate mismatch or expired')
            if mandate_id in state['used_mandates'] or work_item_id in state['work_item_effects']:
                raise RunnerError('mandate or work item already consumed')
            bindings = []
            if p['operation'] == 'REPAIR':
                review = groups['REVIEW'][0]
                rr = state['review_records'].get(review['id'])
                if rr is None or rr['work_item_id'] != work_item_id:
                    raise RunnerError('missing exact triage review')
                ids = item['complaint_ids']
                bindings = self._bindings(state, ids)
                if ids != self._held(state) or rr['bindings'] != bindings or review['challenge_digest'] != digest('ComplaintBindings', bindings):
                    raise RunnerError('repair must bind ALL current complaint versions')
                review_grant = self._grant(state, rr['grant_id'], 'REVIEW', review['actor'], consume=False)
                if rr['grant_digest'] != digest('TriageGrant', review_grant) or rr['grant_id'] not in state['used_grants']:
                    raise RunnerError('review grant binding mismatch')
                others = [a for a in self._history(state) + participants if a != review['actor']] + [executor]
                self._review_independence(state, review['actor'], ids, others)
                self._independent(authorizer, state['participants'])
                self._claimant_independence(state, authorizer, ids)
                self._claimant_independence(state, executor, ids)
                # Factfinders are disqualified from repair authorization and execution.
                finders = [f['actor'] for f in state['factfinding_records']]
                self._independent(authorizer, finders); self._independent(executor, finders)
            elif self._held(state):
                raise RunnerError('unresolved complaint hold')
            effect = dict(schema='cortac.scratch.triage.effect.v1', id='effect-' + str(state['revision'] + 1),
                          case_id=p['case_id'], policy_digest=self._policy_digest,
                          triage_digest=self._triage_digest, proposal_digest=pd,
                          mandate_digest=digest('Mandate', grant), receipt_digests=[digest('Receipt', r) for r in receipts],
                          before_revision=state['revision'], after_revision=state['revision'] + 1,
                          before_value=state['value'], after_value=p['value'], executor=executor,
                          work_item_id=work_item_id, complaint_bindings=bindings,
                          scope=SCOPE, provenance='SYNTHETIC_FIXTURE')
            state['revision'] += 1; state['value'] = p['value']
            state['used_mandates'].append(mandate_id); state['effects'].append(effect)
            state['participants'] = sorted(set(state['participants'] + participants + [executor]))
            self._remember(state, participants + [executor])
            state['pending_audit'] = effect['id']; state['work_item_effects'][work_item_id] = effect['id']
            for binding in bindings:
                state['complaints'][binding['id']]['appeal_status'] = 'REPAIR_PENDING_AUDIT'
            return effect
        key = 'repair' if type(p) is dict and p.get('operation') == 'REPAIR' else 'ordinary'
        return self._run_budget('commit', [key], commit)

    def audit(self, effect, actor, grant_id):
        effect = deepcopy(effect)
        if type(effect) is not dict or type(effect.get('work_item_id')) is not str:
            raise RunnerError('triage effect required')
        item_id = effect['work_item_id']
        def audit(state):
            g = self._grant(state, grant_id, 'AUDIT', actor)
            if g['work_item_id'] != item_id or g['proposal_digest'] != effect['proposal_digest']:
                raise RunnerError('audit grant effect/work item mismatch')
            if not state['effects'] or digest('Effect', effect) != digest('Effect', state['effects'][-1]) or state['pending_audit'] != effect['id']:
                raise RunnerError('audit effect not current')
            if state['value'] != effect['after_value'] or state['revision'] != effect['after_revision']:
                raise RunnerError('audit state mismatch')
            if g['complaints'] != self._grant_bindings(effect['complaint_bindings']):
                raise RunnerError('audit grant complaint binding mismatch')
            self._independent(actor, self._history(state) + self._policy['excluded_ids'] + [g['authorizer']])
            bound_ids = [b['id'] for b in effect['complaint_bindings']]
            self._claimant_independence(state, actor, bound_ids)
            self._support_independence(state, g, bound_ids)
            resolved = []; preserved = []
            for binding in effect['complaint_bindings']:
                c = state['complaints'][binding['id']]
                if c['version'] != binding['version'] or c['current_digest'] != binding['complaint_digest']:
                    preserved.append(c['id']); continue
                resolution = dict(effect_digest=digest('Effect', effect), complaint_digest=c['current_digest'],
                                  version=c['version'], auditor=actor, grant_id=grant_id,
                                  result='AUDITED_SCRATCH_REPAIR')
                c['resolution'] = resolution; c['resolutions'].append(resolution)
                c['hold'] = False; c['appeal_status'] = 'RESOLVED'; resolved.append(c['id'])
            state['pending_audit'] = None
            state['used_grants'].append(grant_id)
            state['participants'] = sorted(set(state['participants'] + [actor])); self._remember(state, [actor])
            record = dict(schema='cortac.scratch.triage.audit.v1', effect_digest=digest('Effect', effect),
                          work_item_id=item_id, observed_value=state['value'], observed_revision=state['revision'],
                          auditor=actor, grant_id=grant_id, grant_digest=digest('TriageGrant', g),
                          resolved_complaints=resolved, preserved_changed_complaints=preserved,
                          remaining_holds=self._held(state), scope=SCOPE,
                          result='MATCHED_SCRATCH_STATE', authority='NONE',
                          controller_closure='SUPPLIED_UNVERIFIED', provenance='SYNTHETIC_FIXTURE')
            state['audit_records'].append(record)
            return record
        def select(g, _state):
            if g['work_item_id'] != item_id or g['proposal_digest'] != effect.get('proposal_digest'):
                raise RunnerError('audit request outside pinned grant scope')
            return ['audit:' + item_id]
        return self._protected('AUDIT', actor, grant_id, select, audit)

    def revoke_grant(self, grant_id, actor, reason):
        def revoke(state):
            text(grant_id, 'grant ID'); text(reason, 'revocation reason')
            if grant_id not in self._grants:
                raise RunnerError('unknown triage grant')
            g = self._grants[grant_id]
            self._actor(actor, 'authorizer')
            if actor != g['authorizer']:
                raise RunnerError('revocation requires exact pinned grant authorizer')
            if grant_id in state['revoked_grants']:
                raise RunnerError('triage grant already revoked')
            record = dict(schema='cortac.scratch.triage.revocation.v1', grant_id=grant_id,
                          grant_digest=digest('TriageGrant', g), actor=actor, reason=reason,
                          tick=state['tick'], scope=SCOPE, provenance='SYNTHETIC_FIXTURE')
            state['revoked_grants'][grant_id] = record
            self._remember(state, [actor])
            return record
        return self._run_budget('revoke_grant', ['ordinary'], revoke)

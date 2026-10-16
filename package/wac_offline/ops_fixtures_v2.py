"""Exposed fabricated v2 examples. Not real case evidence."""
from copy import deepcopy
from .ops_fixtures_v1 import fixture as legacy_fixture
from .ops_trace_v2 import VERSION, CONTEXT_VERSION, STAGES, digest


def bind(trace, context):
    """Construct supplied links for examples, never authenticate them."""
    trace['context_digest'] = digest(context)
    trace['remedy']['findings_digest'] = digest(trace['findings'])
    previous, prior_digest = 'NONE', digest(trace['findings'])
    for event in trace['remedy']['events']:
        event['previous_id'], event['previous_digest'] = previous, prior_digest
        previous, prior_digest = event['id'], digest(event)


def fixture(stages=STAGES):
    trace, context = legacy_fixture()
    trace['schema'], context['schema'] = VERSION, CONTEXT_VERSION
    trace['remedy']['mode'] = 'VOLUNTARY_REPORTED'
    context['now'] = 60
    trace['remedy']['deadline'] = 80
    trace['remedy']['escalation']['due_at'] = 90
    context['authorizations'] = [dict(id='grant-' + actor, binding=deepcopy(trace['binding']),
        remedy_id='remedy', remedy_version=1, actor=actor, issuer='reviewer',
        stages=list(STAGES) + ['REFUSED'], start=10, end=100, state='CURRENT_REPORTED')
        for actor in ('owner', 'verifier')]
    trace['reassessments'] = [dict(deepcopy(trace['independence']), id='assessment-1',
        previous_id='INITIAL', checked_at=10, reassess_at=100)]
    trace['remedy']['events'] = []
    attempt, observations, audits = None, [], []
    for i, stage in enumerate(stages):
        identity, evidence_id, at = 'event-' + str(i), 'evidence-' + str(i), 11+i
        ev = dict(id=evidence_id, version=1, digest=digest(evidence_id), kind=stage, observed_at=at)
        context['evidence'].append(ev)
        actor = 'verifier' if stage == 'AUDITED' else 'owner'
        targets = [] if i == 0 else ['event-' + str(i-1)]
        if stage == 'ATTEMPTED':
            attempt, observations, audits = identity, [], []
        if stage == 'OBSERVED':
            targets = [attempt]
            observations.append(identity)
            audits = []
        if stage == 'AUDITED':
            targets = list(observations)
            audits.append(identity)
        if stage == 'EFFECTIVENESS_REPORTED':
            targets = list(audits)
        trace['remedy']['events'].append(dict(id=identity, stage=stage,
            previous_id='NONE', previous_digest='0'*64, at=at, actor=actor,
            reason='Fabricated transition rationale',
            outcome='REPAIR_REPORTED' if stage == 'AUDITED' else 'NOT_APPLICABLE',
            evidence_refs=[{k: ev[k] for k in ('id', 'version', 'digest')}], targets=targets,
            authorization_ref='grant-' + actor, assessment_ref='assessment-1' if stage == 'AUDITED' else 'NONE'))
    trace['remedy']['residuals'][0].update(state='REPAIRED_REPORTED' if audits else 'UNRESOLVED',
        observation_ids=list(observations), audit_ids=list(audits))
    next(e for e in context['evidence'] if e['id'] == 'account')['observed_at'] = 11+len(stages)-1 if stages else 10
    bind(trace, context)
    return trace, context

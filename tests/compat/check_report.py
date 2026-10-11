#!/usr/bin/env python3
"""Gate a strict differential report against explicitly reviewed changes.

The runner remains strict. This checker compares actual payloads again, applying
only bounded transformations from expectations.json. It does not prove complete
library/application compatibility or replace candidate safety checks.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path

from runner import differences

DEFAULT_EXPECTATIONS = Path(__file__).with_name('expectations.json')


class GateError(ValueError):
    pass


def _equal(left, right, tolerance):
    return not differences(left, right, **tolerance)


def _at(value, location):
    for key in location:
        value = value[key]
    return value


def _replace(value, location, replacement):
    if not location:
        return copy.deepcopy(replacement)
    _at(value, location[:-1])[location[-1]] = copy.deepcopy(replacement)
    return value


def _loops(loops):
    """Preserve coordinates, winding, multiplicity, and explicit closure."""
    normalized = []
    for loop in loops:
        if not isinstance(loop, list):
            raise GateError('contour is not a list')
        if any(not isinstance(p, list) or len(p) != 3 or
               any(type(x) not in (int, float) or not math.isfinite(x) for x in p)
               for p in loop):
            raise GateError('invalid contour coordinates')
        if not loop:
            normalized.append([])
            continue
        closed = len(loop) > 1 and loop[0] == loop[-1]
        points = loop[:-1] if closed else loop
        rotations = [points[i:] + points[:i] for i in range(len(points))]
        rotated = min(rotations)
        normalized.append(rotated + [rotated[0]] if closed else rotated)
    return sorted(normalized)


def _normalize(value, rule, side, tolerance):
    value = copy.deepcopy(value)
    shape = rule.get('contours')
    if shape == 'stack':
        value = [[height, _loops(loops)] for height, loops in value]
    elif shape == 'layers':
        value = [_loops(loops) for loops in value]
    elif shape == 'loops':
        value = _loops(value)
    elif shape == 'algorithm':
        # Preserve all other fields, including threads and all fiber contacts.
        for layer in ('first', 'reset', 'second'):
            value[layer]['loops'] = _loops(value[layer]['loops'])
    elif shape == 'weave':
        value['loops'] = _loops(value['loops'])
    elif shape is not None:
        raise GateError('unknown contour shape')
    if side == 'candidate':
        for addition in rule.get('empty_fibers', []):
            fibers = _at(value, addition['location'])
            empty = [f for f in fibers if f.get('intervals') == []]
            if not _equal(empty, addition['expected'], tolerance):
                raise GateError('unexpected added empty fiber data at ' + str(addition['location']))
            value = _replace(value, addition['location'],
                             [f for f in fibers if f.get('intervals') != []])
    return value


def _check_case(case, rule, tolerance):
    reference, candidate = case['reference'], case['candidate']
    # These cannot be accepted, even for a reviewed constructor/extension case.
    for side in (reference, candidate):
        if side['status'] not in ('ok', 'error'):
            raise GateError('crash, timeout, or protocol failure: ' + side['status'])
    kind = rule.get('kind', 'compare')
    if kind == 'removed_constructor':
        if (reference['status'] != 'ok' or candidate['status'] != 'error'
                or not _equal(reference['value'], rule['reference_value'], tolerance)
                or candidate.get('exception') != rule['candidate_exception']
                or candidate.get('message') != rule['candidate_message']):
            raise GateError('constructor rejection differs from reviewed contract')
        return
    if kind == 'candidate_only':
        if (reference['status'] != 'error' or candidate['status'] != 'ok'
                or reference.get('exception') != rule['reference_exception']
                or reference.get('message') != rule['reference_message']):
            raise GateError('unexpected reference/candidate extension outcome')
        value = _normalize(candidate['value'], rule, 'candidate', tolerance)
        if not _equal(value, rule['candidate_value'], tolerance):
            raise GateError('candidate-only semantic result changed')
        return
    if kind != 'compare':
        raise GateError('unknown expectation kind')
    if reference['status'] != 'ok' or candidate['status'] != 'ok':
        raise GateError('unexpected Python exception')
    left = _normalize(reference['value'], rule, 'reference', tolerance)
    right = _normalize(candidate['value'], rule, 'candidate', tolerance)
    for transition in rule.get('transitions', []):
        location = transition['location']
        if (not _equal(_at(left, location), transition['reference'], tolerance)
                or not _equal(_at(right, location), transition['candidate'], tolerance)):
            raise GateError('reviewed property transition changed at ' + str(location))
        right = _replace(right, location, _at(left, location))
    changes = differences(left, right, **tolerance)
    if changes:
        raise GateError('unapproved difference at ' + changes[0]['path'])
    # Preserve the one observable native-printing contract compared by runner.
    if rule.get('compare_stdout') and reference.get('stdout') != candidate.get('stdout'):
        raise GateError('native stdout changed')


def check_report(report, expectations):
    """Return all failures; do not trust report status/count/difference summaries."""
    failures = []
    try:
        if report['schema_version'] != 1 or expectations['schema_version'] != 1:
            raise GateError('unsupported schema')
        tolerance = expectations['tolerances']
        if any(type(tolerance[k]) not in (int, float) or not math.isfinite(tolerance[k])
               or tolerance[k] < 0 for k in ('rtol', 'atol')):
            raise GateError('invalid expectation tolerances')
        inventories = report['inventories']
        for name in ('reference', 'candidate'):
            if inventories[name]['status'] != 'ok':
                raise GateError(name + ' inventory failed')
        metadata = inventories['reference']['value']['metadata']
        if metadata['distribution'] != expectations['reference_distribution']:
            raise GateError('wrong reference distribution')
        observed_api = differences(inventories['reference']['value']['api'],
                                   inventories['candidate']['value']['api'])
        if observed_api != expectations['api_transitions']:
            failures.append('API changes differ from explicitly reviewed transitions')
        if set(report['cases']) != set(expectations['required_cases']):
            failures.append('missing or unexpected cases: full report required')
        if report['coverage']['uncovered']:
            failures.append('uncovered API members remain')
        rules = expectations['cases']
        if set(rules) - set(expectations['required_cases']):
            raise GateError('manifest contains rules for unknown cases')
        outcomes = {}
        for name, case in report['cases'].items():
            try:
                _check_case(case, rules.get(name, {}), tolerance)
                outcomes[name] = True
            except (GateError, KeyError, TypeError, IndexError, ValueError) as exc:
                outcomes[name] = False
                failures.append(name + ': ' + str(exc))
        # Raw contour acceptance depends on a separately executed geometry case.
        for name, rule in rules.items():
            pair = rule.get('paired_case')
            if pair and (not outcomes.get(name) or not outcomes.get(pair)):
                failures.append(name + ': paired geometry check missing or failed: ' + pair)
    except (GateError, KeyError, TypeError, ValueError) as exc:
        failures.append('invalid report/manifest: ' + str(exc))
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--expectations', type=Path, default=DEFAULT_EXPECTATIONS)
    args = parser.parse_args(argv)
    try:
        report = json.loads(args.report.read_text(encoding='utf-8'))
        expectations = json.loads(args.expectations.read_text(encoding='utf-8'))
        failures = check_report(report, expectations)
    except (OSError, ValueError) as exc:
        failures = ['cannot read report/manifest: ' + str(exc)]
    for failure in failures:
        print(failure)
    if not failures:
        print('Reviewed compatibility gate passed; strict report still records intentional differences.')
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())

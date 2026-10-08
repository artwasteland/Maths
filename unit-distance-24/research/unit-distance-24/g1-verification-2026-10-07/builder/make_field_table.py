#!/usr/bin/env python3
"""Annotate every enumerated leaf, including fields that are only provenance."""
import json
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
data = json.loads((BASE / 'outputs-r2/field-enumeration-complete.json').read_text())
rows = []
def row(kind, field, status, binding, limitation=''):
    rows.append(dict(file=kind, field=field, status=status, binding=binding, limitation=limitation))

def classify(kind, field):
    # These explicit schemas, not name searches, cover the union of every file
    # and decoded export in all selected copies and both fixture formats.
    N = ('N', '—', 'Timing, execution history, tool provenance, or explanatory text; not an output-content measurement.')
    H = ('H', 'No independent post-deletion measurement', 'Can misstate deleted content/processing. The producer/checker measured it before deletion; resealing does not repeat that check.')
    if kind in ('stage', 'export-stage'):
        if field in ('children_written', 'children_file_sha256'):
            return ('B', 'RA:280,281; exports RA:488 / E:242', 'Retained full output is measured directly; deleted exported levels use historical inventory rows.')
        if field == 'inputs_sha256.*':
            return ('B', 'RA:429,432; E:264', 'All retained/reconstructed inputs and pinned data are hashed; other deleted inputs are historical only.')
        if field in ('parent_file', 'parent_range[]') or field.startswith('parent_sources[].'):
            return ('B', 'RA:293–313; E:246–294', 'Retained sources are measured; all-shipped parents are concatenated and measured. Deleted sources/parents use pre-deletion inventory.')
        if field.startswith('reach.'):
            return ('B', 'RA:319; E:31 / C:303–351', 'Reach hash measured; thresholds/tables derived from checked reach/configuration.')
        if field.startswith('pruning.') or field in ('forbidden_set', 'exit_status'):
            return ('B', 'RA:282–287', 'Retained producer policy equals the checked configuration/pass verdict; deleted exports are historical for these flags.')
        return N
    if kind == 'export-shard':
        if field in ('children_written', 'children_file_sha256', 'parent_range[]'):
            return ('H', 'RA:488 / E:271–294; originally E:109,236', 'Compared with historical inventory and tiling/count totals. Shard bytes were measured before deletion; their exact contents cannot be re-read.')
        if field == 'inputs_sha256.*':
            return ('B', 'RA:429,432', 'Any retained/reconstructed input is measured. Other deleted inputs are historical, and arbitrary deleted input-map entries are not rechecked.')
        if field in ('parent_file', 'exit_status'):
            return ('H', 'No current value check; originally C:707–721', 'Can mislabel a deleted shard input or success. The original full-directory check checked the shard before deletion.')
        return N
    if kind == 'prune':
        if field == 'counts.tri_silent_passes' or field == 'triangles_silent_passes':
            return ('H', 'RA:383–388,412; originally E:210–231', 'Only reconciled with diagnostic sums now. Silent passes have no distinguishing retained certificate; stderr was measured before deletion.')
        if field.startswith('counts.') or field.startswith('verified_counts.'):
            return ('B', 'RA:332–398; E:181', 'Certificate verdicts/rule tags and measured output records derive every category, apart from silent diagnostics above.')
        if field == 'checker':
            return ('B', 'RA:333–357,403–407', 'Records/verdict/rule counters and native proof-tree node counts derive from certificates. Proof validity itself was checked by the original kernel.')
        if field in ('inputs_sha256.*', 'outputs_sha256.*'):
            return ('B', 'RA:173–178,429,432', 'Every retained/reconstructed naming-map value is hashed independently. Deleted-only intermediate output-map values are not measured now.')
        if field in ('level_file', 'level[]', 'kind', 'target[]', 'forbidden_set', 'filter_set', 'triangles', 'exit_status', 'problems[]', 'mutation.unknown_as_pruned'):
            return ('B', 'RA:170–171,363–368', 'Cell/input identity, policy and success agree with the filename, checked configuration and accepted receipt.')
        if field.startswith('embedder.') or field in ('tu_rule_bound.n', 'tu_rule_bound.proved_upper_bound'):
            return ('B', 'RA:369–375,417', 'Filter-only policy matches configuration; survivors are certificate-derived; the TU bound matches the pinned (24,69) target.')
        if field.startswith('triangles_checker.') or field == 'triangles_prover.witness':
            return ('B', 'RA:413–415 / T:876', 'Witness tag and checker command bind the expected cell/stage files, dataset, interpreter descriptor and non-environment checker choice; relocation preserves original paths.')
        if field.startswith('triangles_stats.'):
            if field.split('.')[-1] in ('graphs', 'tu', 'refuted', 'pass'):
                return ('B', 'RA:409–411', 'Derived from retained certificate categories and measured outputs.')
            if field.split('.')[-1] in ('budget_limit', 'max_nodes', 'mirror'):
                return N
            return ('H', 'RA:383–388 checks four diagnostic types only; originally E:210–231', 'Deleted prover stderr/JSONL supplied these counters. Other tree/leaf/open counters have no current value binding; altering them can falsify prover processing history.')
        return N
    if kind == 'verify':
        if field in ('records', 'stage_sha256', 'stage_kind'):
            return ('B', 'RA:225–230', 'Retained stages use measured rows; deleted stages use pre-deletion inventory.')
        if field in ('stage_file', 'parents_seen', 'parts[].range[]') or field.startswith('parts[].udenum_stats.') and field.split('.')[-1] not in ('wall_seconds', 'cpu_seconds', 'max_rss_kib'):
            return ('B', 'RA:438–459', 'Stage identity/count, part tiling and seen/skipped counts bind to stage records; no-generation counters bind to the checked verification target contract. Deleted stages remain historical.')
        if field in ('kind', 'level[]', 'exit_status', 'forbidden_set', 'check', 'udenum_target[]', 'forbidden_sha256'):
            return ('B', 'RA:439–443', 'Filename/configuration derive identity, operation and target; pinned forbidden data are hashed.')
        if field.startswith('parts[].udenum_manifest'):
            return ('H', 'No current part-file SHA/path measurement; originally D:890–912', 'Deleted part manifest was hashed by the producer. Can mislabel or replace the claimed digest of that deleted output.')
        return N
    if kind == 'hashes.json':
        return ('B', 'RA:653–668', 'File set/slice derived; retained SHA/records measured, deleted rows historical; aggregate digest recomputed.')
    if kind == 'counts.json':
        if field.endswith('tri_silent_passes'):
            return ('H', 'RA:396–401,669–671; originally E:210–231', 'Matches summary/diagnostic counts, but deleted prover stderr cannot be remeasured.')
        return ('B', 'RA:198–200,396–401,669–671', 'Positional n,m,children and all twelve prune categories equal the checked summary; retained categories derive from bytes, silent diagnostics/deleted levels remain historical.')
    if kind == 'inventory-row':
        return ('B', 'RA:25,68–72,262–269', 'Typed unique paths; every retained row SHA/bytes/newlines measured. Deleted rows themselves cannot be independently remeasured.')
    if kind == 'inventory-header':
        if field == 'prefix_through':
            return ('B', 'RA:38–42', 'Fixed prefix through level 12.')
        return ('H', 'RA:38–42 type checks only; originally W:100–134', 'Prefix files/bytes/digest cover deleted files. Alterations can misstate original prefix totals; no current recomputation.')
    if kind == 'reach.json':
        if field in ('root_k_source', 'ubar_justification'):
            return N
        return ('B', 'RA:610–611 / E:31 / C:242–351', 'Target/seed/u-bar, override bounds, root threshold, windows and L4 table checked/derived from configuration and justified bounds.')
    if kind == 'run-config.json':
        if field in ('prune_max_states', 'prune_tries', 'ubar_justification'):
            return N
        if field.startswith('ubar_override.'):
            return ('B', 'RA:255 / C:242', 'Both numeric override claims equal the checked reach.json override values.')
        return ('B', 'RA:579–581,615 / E:31; J:348–358', 'Configuration is measured and supplies obligations; identity/pipeline pins and producer policy are reconciled. This is the policy root, not an extra output measurement.')
    if kind == 'run-summary.json' or kind == 'structure' and field.startswith('summary.'):
        field = field[len('summary.'):] if kind == 'structure' else field
        if field.startswith('levels[].prune.counts.'):
            if field.endswith('tri_silent_passes'):
                return ('H', 'RA:396–400 / E:210–231', 'Retained-cell silent count agrees with diagnostics; deleted diagnostics cannot be remeasured.')
            return ('B', 'RA:203–230,396–400', 'Retained-cell categories are certificate-derived; deleted levels use inventory and the original full-directory checker.')
        if field == 'levels[].prune.checker':
            return ('B', 'RA:401–402', 'Retained-cell duplicate equals the measured-counter-checked prune checker line. Deleted-cell checker strings have no current binding.')
        if field in ('levels[].children', 'levels[].reach.input', 'levels[].reach.kept', 'levels[].reach.dropped', 'levels[].verify.records'):
            return ('B', 'RA:210–227,374–380', 'Retained graph/keep/UNKNOWN records measured; reach reconstructed from certificates. Other levels use historical inventory.')
        if field in ('levels[].parents', 'levels[].parent_sources[].records', 'levels[].shards[].children', 'levels[].shards[].range[]'):
            return ('B', 'RA:511–553,307–313', 'Sources/parent count and shard tiling checked; retained source rows measured and parents reconstructed when all sources ship. Deleted shard distribution remains inventory evidence.')
        if field == 'levels[].verify.parts':
            return ('B', 'RA:461–465', 'Equals the actual retained verification manifest part-list length, when this summary field is present.')
        if field.startswith('ubar_override.'):
            return ('B', 'RA:257 / C:242', 'Numeric duplicates equal the checked reach.json override.')
        if field in ('forbidden_set', 'prune_filter_set', 'triangles', 'verify_stages', 'reach.enabled', 'prune.prune_filter_only'):
            return ('B', 'RA:259–263', 'Duplicate policy fields equal the checked configuration.')
        if field in ('completed_through_n', 'levels[].kind', 'levels[].m', 'levels[].n', 'levels[].parent_edge_counts[]', 'levels[].parent_sources[].kind', 'levels[].parent_sources[].level[]', 'levels[].prune.source', 'levels[].reach.k', 'levels[].reach_k', 'prune.enabled', 'prune.prune_from', 'reach.levels.*[]', 'reach.root_k', 'seed_n', 'slice[]', 'target[]', 'windows.*[]'):
            return ('B', 'RA:610–611 / E:31–86 / C:271–397', 'Derived required cells, allowed sources/stages, reach thresholds/windows and target/configuration identity.')
        return N
    if kind == 'structure':
        if field == 'target_counts.tri_silent_passes':
            return ('H', 'RA:122–142; originally E:210–231', 'Matches diagnostic sums, but deleted prover stderr cannot be remeasured.')
        if field.startswith('target_files.') or field.startswith('target_counts.'):
            return ('B', 'RA:92–144', 'Target records/SHA/bytes and categories derive from retained files/certificates; silent diagnostics remain historical.')
        if field.startswith('file_counts.') or field in ('files_digest', 'retained.*', 'run_summary_sha256'):
            return ('B', 'RA:147–163,262–269,641–672', 'Retained measurements and computed digest/summary SHA bind these values; deleted file_counts entries are historical inventory.')
        if field.startswith('manifests.'):
            return ('B', 'RA:491–499,672–677', 'Export text bytes/SHA equal inventory; a retained counterpart must match its measured bytes. Decoded content is separately enumerated below.')
        if field.startswith('prefix_receipt.'):
            return ('B', 'RA:589–609', 'Safe name, actual prefix-structure SHA and recursive whole-receipt validation.')
        if field.startswith('g4.'):
            return ('B', 'RA:678–680 / E:484–537', 'Exact copy of measured fingerprint.json; see its own rows for semantic/historical limits.')
        if field in ('schema', 'result', 'slice[]', 'target[]'):
            return ('B', 'RA:575–578', 'Required schema/pass/identity checked.')
        return N
    if kind == 'known':
        if field.startswith('cells.*.files.'):
            return ('H', 'J:407–440 / known_graphs.py:198–225; originally known_graphs.py:164', 'Membership/count claims are constrained by catalogue/partition/predicted indices, but actual level-16–22 graph files are deleted; no current file measurement.')
        if field.startswith('cells.') or field == 'schema':
            return ('B', 'J:407–440 / known_graphs.py:198–225', 'Dataset names/counts/SHA and eligibility pinned to the shipped catalogue; scope derived from checked reach.')
        if field in ('reach_sha256', 'run_config_sha256'):
            return ('B', 'J:373–375', 'Measured retained reach/configuration SHA.')
        if field in ('result', 'problems[]', 'slice[]', 'target[]'):
            return ('B', 'RA:584–588', 'Pass/identity checked.')
        return N
    if kind == 'receipt-inventory':
        if field in ('sha256', 'bytes', 'prefix.bytes', 'prefix.files', 'prefix.prefix_through', 'prefix.sha256'):
            return ('B', 'RA:475–482', 'Compressed envelope SHA/size measured; prefix duplicate equals header, whose deleted-content limits are listed separately.')
        return ('H', 'No current total check; originally W:100–134', 'Original file/file-byte/directory-byte totals include deleted files and directory inodes. Alterations can falsify original disk footprint or file totals.')
    if kind == 'receipt-checker':
        if field in ('target[]', 'seed_n', 'slice[]', 'pinned.seed', 'pinned.slices[]', 'pinned.target[]', 'certs_replayed', 'pruned_cells_inspected'):
            return ('B', 'RA:582 / W:144–170', 'Identity pins; replayed/pruned counters must be positive and equal. Their exact historical totals are not independently remeasured.')
        if field == 'run':
            return N
        return ('H', 'No current numeric/value comparison; originally C:check_level and main', 'Checker-reported inspected files/cells/shards and processing policy before deletion. Changing them can falsify checking history; required retained presence is derived separately.')
    if kind == 'replay/fingerprint.json':
        if field in ('fingerprint', 'prefix_fingerprint'):
            return ('H', 'E:394–407,516 only recompute with raw run; RA uses run=None; E:468–481 compares prefix', 'Opaque digest includes deleted aggregate parent-input descriptors, not all preserved in v1 receipts. Original evidence check recomputed it; now only cross-prefix equality/retained envelope binds it. Retained contributions are measured individually.')
        if field in ('replay_wall_seconds', 'run_dag2_wall_seconds'):
            return N
        if field in ('sampled_parents', 'production_children_compared', 'mismatching_parents', 'red_all', 'stages_checked'):
            return ('H', 'E:484–537 / C:730–850', 'Checked against replay detail totals/constraints; the deleted replay comparisons themselves cannot be repeated. Alterations of mutually consistent details can falsify historical comparisons.')
        return ('B', 'RA:678–680 / E:484–537 / C:730–850', 'Identity/mode/settings/verdict and aggregate counters equal checked replay details; deleted replay computation itself is historical.')
    if kind in ('replay/summary.json', 'replay/red.json'):
        if any(word in field for word in ('seconds', 'wall_seconds')) or field in ('host', 'workers', 'tool'):
            return N
        if field in ('forbidden_sha256', 'per_cell[].strata', 'per_cell[].stratum'):
            return ('H', 'No current receipt-audit comparison; originally replay-398.py', 'Can falsify the deleted replay input/stratification descriptor. Required sampling is separately derived from audited shard ranges.')
        if field.startswith('stages.') or field.startswith('stages[]'):
            return ('B', 'E:417–465 / T:395–436', 'Stage/input counts, identities, reach parameters and required parent-source coverage are derived from audited stages. Retained stage counts are measured; deleted stages are historical.')
        if (kind == 'replay/red.json' or field.startswith(('red_controls[]', 'seeds[]', 'per_cell[]', 'per_level[]'))
                or field in ('all_identical', 'enum2_children_compared', 'mismatching_parents', 'processed_parents', 'production_children_compared', 'red_all', 'sampled_parents', 'stages_checked', 'stages_ok', 'unreplayable_cells[]')):
            return ('H', 'E:484–537 / C:730–850 / T:248–393,521', 'Details/aggregate sums, prescribed samples, full seeds and red transformations are checked against audited scope. Raw replay comparisons/seed outputs are deleted; altering mutually consistent historical comparisons may still pass. Retained-stage records are independently checked in the stage rows above.')
        return ('B', 'E:484–537 / C:730–850 / T:248–393,521', 'Totals/results derive from detail rows; scope/sample indices, full seeds and red transformations are constrained by audited cells. Comparisons involving deleted replay outputs cannot be rerun from these JSON summaries alone.')
    raise AssertionError((kind, field))

for kind, fields in sorted(data['schemas'].items()):
    for field in fields:
        row(kind, field, *classify(kind, field))

# Non-JSON receipt claims are explicitly enumerated as well.
for kind in ('inventory', 'known', 'structure'):
    for field in ('sha256', 'bytes'):
        row('receipt-text', kind + '.' + field, 'B', 'RA:569–572,477–478', 'Actual envelope SHA/byte size.')
for field in ('records', 'bytes', 'sha256'):
    row('receipt-text', 'target_files.*.' + field, 'B', 'RA:484', 'Equals independently measured target_files.')
for key in ('input', 'tu', 'survivors', 'tri_tu', 'tri_refuted', 'tri_silent_passes', 'tri_survivors', 'embedded', 'refuted', 'unknown', 'kept', 'pruned'):
    row('receipt-text', 'target_counts.' + key, 'H' if key == 'tri_silent_passes' else 'B', 'RA:485', 'Equals target_counts; silent diagnostic limitation as above.')
for field in ('level_files_checked.files', 'level_files_checked.sha256'):
    row('receipt-text', field, 'B', 'RA:483 / RA:664–668', 'Equals recomputed file count/digest; deleted components are historical inventory.')
for field in ('worker.verdict', 'chain.verdict', 'evidence.g4_result'):
    row('receipt-text', field, 'B', 'RA:562–564,582,680 / E:484', 'Pass/coverage-mode/G4 verdict checked; detailed semantics independently reconciled.')
for field in ('run.regular_file_bytes', 'prefix_comparison.files', 'shared_prefix.sha256', 'coverage.required_cells', 'coverage.certs_replayed', 'known_cells.full_records', 'known_cells.reach_records', 'known_cells.keep_records', 'known_cells.cells', 'known_cells.forms_kept', 'evidence.recovered_cells'):
    row('receipt-text', field, 'H', 'RA:601–603 compares shared-prefix digests only; other duplicates not checked', 'Original worker/checker/control measured the deleted run/prefix/cells or execution history. Alterations can falsify historical totals/digests; retained content is independently measured elsewhere.')
for field in ('checker.sha256', 'control.sha256', 'worker.sha256', 'launcher.sha256', 'evidence_tool.sha256', 'runbook.sha256', 'branch_HEAD', 'python', 'host', 'measured.*', 'run_directory', 'prefix_origin', 'retained_snapshot', 'push_status'):
    row('receipt-text', field, 'N', 'RA:565 pins the chain checker; others historical descriptors', 'Tool/runtime/location/publication provenance rather than output-content fields.')
for field in ('g6', 'verdict', 'witness{*}'):
    row('certificates (payload)', field, 'B', 'RA:92–111,332–357,377–407', 'Ordered graph streams, verdict/category counters and native proof-node counts reconstructed; payload bytes hashed. Mathematical witness validity relies on the original kernel replay, not this metadata scan.')

counts = Counter(r['status'] for r in rows)
groups = defaultdict(list)
for r in rows:
    groups[(r['file'], r['status'], r['binding'], r['limitation'])].append(r['field'])
lines = ['| File / field families (every name is listed) | Status | Audit binding / limitation |', '| --- | --- | --- |']
for (kind, status, binding, limitation), fields in sorted(groups.items()):
    labels = ', '.join('`' + field + '`' for field in sorted(fields))
    lines.append(f'| {kind}: {labels} | {status} | {binding}. {limitation} |')
(BASE / 'outputs-r2/field-table.md').write_text('\n'.join(lines) + '\n')
(BASE / 'outputs-r2/field-bindings.json').write_text(json.dumps(dict(total=len(rows), counts=dict(counts), fields=rows), indent=2) + '\n')
print(json.dumps(dict(total=len(rows), counts=dict(counts), table_rows=len(groups))), flush=True)

#!/usr/bin/env python3
"""
Batch parser for all 34 volumes of the Fankha corpus.
Generates sources/json/fahares_vol_01.json to fahares_vol_34.json
and calculates comprehensive corpus-wide statistics.
"""

import os
import sys
import time
import json
from dataclasses import asdict
from typing import Dict, Any

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fankha_parser import FankhaParser

def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    corpus_text_dir = os.path.join(repo_root, "text")
    if not os.path.isdir(corpus_text_dir):
        corpus_text_dir = os.path.join(repo_root, "sources/text")

    output_dir = os.path.join(repo_root, "json")
    os.makedirs(output_dir, exist_ok=True)

    volumes_stats = []
    grand_start_time = time.time()

    total_corpus_works = 0
    total_corpus_referrals = 0
    total_corpus_manuscripts = 0
    total_corpus_clean_mss = 0
    total_corpus_residuals_mss = 0

    print("=" * 80)
    print("STARTING BATCH PARSING OF ALL 34 VOLUMES OF FAHARES (FANKHA)")
    print("=" * 80)
    print(f"{'Vol':>4} | {'Time':>7} | {'Works':>7} | {'Refs':>6} | {'MSS':>7} | {'Clean MSS':>9} | {'Clean %':>8} | {'Residuals':>9}")
    print("-" * 80)

    for vol in range(1, 35):
        input_file = os.path.join(corpus_text_dir, f"fahares_vol_{vol:02d}.txt")
        output_file = os.path.join(output_dir, f"fahares_vol_{vol:02d}.json")

        if not os.path.exists(input_file):
            print(f"ERROR: {input_file} not found!")
            continue

        t0 = time.time()
        parser = FankhaParser(vol)
        parser.parse_file(input_file)
        parser.export_json(output_file, indent=2)
        elapsed = time.time() - t0

        works_count = len(parser.works)
        refs_count = len(parser.referrals)
        mss = [m for w in parser.works for m in w.manuscripts]
        mss_count = len(mss)
        clean_count = sum(1 for m in mss if not m.residual_notes)
        residuals_count = mss_count - clean_count
        clean_pct = (clean_count / mss_count * 100) if mss_count > 0 else 0

        total_corpus_works += works_count
        total_corpus_referrals += refs_count
        total_corpus_manuscripts += mss_count
        total_corpus_clean_mss += clean_count
        total_corpus_residuals_mss += residuals_count

        vol_stat = {
            'volume': vol,
            'elapsed_sec': round(elapsed, 2),
            'works': works_count,
            'referrals': refs_count,
            'manuscripts': mss_count,
            'clean_manuscripts': clean_count,
            'clean_pct': round(clean_pct, 2),
            'residual_manuscripts': residuals_count,
            'dates_parsed': sum(1 for m in mss if m.copy_date_raw or m.is_bita),
            'scribes_parsed': sum(1 for m in mss if m.scribe or m.is_bika or m.is_autograph),
            'citations_parsed': sum(1 for m in mss if m.catalog_citation),
            'scripts_parsed': sum(1 for m in mss if m.script or m.scripts),
            'folios_parsed': sum(1 for m in mss if m.folios),
            'lines_parsed': sum(1 for m in mss if m.lines),
            'dimensions_parsed': sum(1 for m in mss if m.dimensions),
            'bindings_parsed': sum(1 for m in mss if m.binding),
            'incipits_matched_or_parsed': sum(1 for m in mss if m.incipit_text or m.incipit_matches_work),
            'explicits_matched_or_parsed': sum(1 for m in mss if m.explicit_text or m.explicit_matches_work),
            'is_autograph': sum(1 for m in mss if m.is_autograph),
            'is_ruled': sum(1 for m in mss if m.is_ruled),
            'is_illuminated': sum(1 for m in mss if m.is_illuminated),
            'is_illustrated': sum(1 for m in mss if m.is_illustrated),
            'is_collated': sum(1 for m in mss if m.is_collated),
            'ownership_and_seals': sum(1 for m in mss if m.ownership_and_seals),
        }
        volumes_stats.append(vol_stat)

        print(f"{vol:4d} | {elapsed:6.2f}s | {works_count:7d} | {refs_count:6d} | {mss_count:7d} | {clean_count:9d} | {clean_pct:7.1f}% | {residuals_count:9d}")

    total_elapsed = time.time() - grand_start_time
    total_clean_pct = (total_corpus_clean_mss / total_corpus_manuscripts * 100) if total_corpus_manuscripts > 0 else 0

    print("-" * 80)
    print(f"{'ALL':>4} | {total_elapsed:6.1f}s | {total_corpus_works:7d} | {total_corpus_referrals:6d} | {total_corpus_manuscripts:7d} | {total_corpus_clean_mss:9d} | {total_clean_pct:7.1f}% | {total_corpus_residuals_mss:9d}")
    print("=" * 80)

    summary = {
        'total_volumes': len(volumes_stats),
        'total_elapsed_seconds': round(total_elapsed, 2),
        'total_works': total_corpus_works,
        'total_referrals': total_corpus_referrals,
        'total_manuscripts': total_corpus_manuscripts,
        'total_clean_manuscripts': total_corpus_clean_mss,
        'overall_clean_percentage': round(total_clean_pct, 2),
        'total_residual_manuscripts': total_corpus_residuals_mss,
        'overall_fields': {
            'dates_parsed': sum(v['dates_parsed'] for v in volumes_stats),
            'scribes_parsed': sum(v['scribes_parsed'] for v in volumes_stats),
            'citations_parsed': sum(v['citations_parsed'] for v in volumes_stats),
            'scripts_parsed': sum(v['scripts_parsed'] for v in volumes_stats),
            'folios_parsed': sum(v['folios_parsed'] for v in volumes_stats),
            'lines_parsed': sum(v['lines_parsed'] for v in volumes_stats),
            'dimensions_parsed': sum(v['dimensions_parsed'] for v in volumes_stats),
            'bindings_parsed': sum(v['bindings_parsed'] for v in volumes_stats),
            'incipits': sum(v['incipits_matched_or_parsed'] for v in volumes_stats),
            'explicits': sum(v['explicits_matched_or_parsed'] for v in volumes_stats),
            'is_autograph': sum(v['is_autograph'] for v in volumes_stats),
            'is_ruled': sum(v['is_ruled'] for v in volumes_stats),
            'is_illuminated': sum(v['is_illuminated'] for v in volumes_stats),
            'is_illustrated': sum(v['is_illustrated'] for v in volumes_stats),
            'is_collated': sum(v['is_collated'] for v in volumes_stats),
            'ownership_and_seals': sum(v['ownership_and_seals'] for v in volumes_stats),
        },
        'volumes': volumes_stats
    }

    os.makedirs("scratch", exist_ok=True)
    summary_path = "scratch/parsing_summary_all_34_volumes.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\nSaved detailed summary to {summary_path}")

if __name__ == "__main__":
    main()
